# recommendation/views.py
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import os
from anime.models import Anime
from .models import RecommendationCache, UserRating
from .engine.recommendation_engine import recommendation_engine
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
import json
import logging
import traceback
from .models import UserInteraction
from .models import UserComment, UserLike, UserFavorite
from users.models import Profile, UserBrowsing
from django.template.loader import render_to_string
from django.db.models import Q
from django.contrib.auth.models import User

# 配置日志记录器
logger = logging.getLogger('django')

# ========================= 页面视图函数 =========================
@login_required
@require_POST
def toggle_anime_like(request, anime_id):
    """
    动漫点赞切换API
    处理用户对动漫的点赞/取消点赞操作
    """
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        from recommendation.models import AnimeLike
        # 检查是否已点赞
        like, created = AnimeLike.objects.get_or_create(
            user=request.user,
            anime=anime
        )

        if not created:
            # 已点赞，取消点赞
            like.delete()
            action = 'removed'
            message = '已取消点赞'
        else:
            # 新增点赞
            action = 'added'
            message = '点赞成功'
        from recommendation.models import AnimeLike
        # 获取最新点赞数
        like_count = AnimeLike.objects.filter(anime=anime).count()

        return JsonResponse({
            'success': True,
            'action': action,
            'message': message,
            'like_count': like_count
        })
    except Exception as e:
        logger.error(f"动漫点赞操作失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': '操作失败，请稍后再试'
        }, status=500)
@login_required
@require_POST
def toggle_like_comment(request, comment_id):
    """
    评论点赞切换API
    处理用户对评论的点赞/取消点赞操作
    """
    try:
        comment = get_object_or_404(UserComment, id=comment_id)

        # 检查用户是否已点赞
        like, created = UserLike.objects.get_or_create(
            user=request.user,
            comment=comment
        )

        if not created:
            # 已点赞，取消点赞
            like.delete()

            # 减少评论点赞计数
            if comment.like_count > 0:
                comment.like_count -= 1
                comment.save(update_fields=['like_count'])

            return JsonResponse({
                'success': True,
                'action': 'removed',
                'like_count': comment.like_count,
                'message': '已取消点赞'
            })
        else:
            # 新增点赞
            comment.like_count += 1
            comment.save(update_fields=['like_count'])

            return JsonResponse({
                'success': True,
                'action': 'added',
                'like_count': comment.like_count,
                'message': '点赞成功'
            })
    except Exception as e:
        logger.error(f"评论点赞操作失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': '操作失败，请稍后再试'
        }, status=500)
@login_required
@require_GET
def get_recommendations(request):
    """获取当前用户的个性化推荐动漫"""
    # 在查询缓存之前净化过期数据
    try:
        RecommendationCache.objects.filter(expires_at__lt=timezone.now()).delete()
    except Exception as e:
        logger.warning(f"清理缓存失败: {str(e)}")

    # 获取请求参数
    strategy = request.GET.get('strategy', 'hybrid')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 12))

    # 验证参数
    valid_strategies = ['hybrid', 'cf', 'content', 'popular', 'ml']
    if strategy not in valid_strategies:
        strategy = 'hybrid'  # 默认回退到混合策略

    if limit > 50:
        limit = 50  # 限制最大结果数

    # 获取用户推荐
    user_id = request.user.id
    try:
        # 简化的错误处理流程
        try:
            # 尝试获取推荐
            recommendations = recommendation_engine.get_recommendations_for_user(
                user_id, limit=limit * 2, strategy=strategy
            )

            # 如果推荐为空，回退到热门推荐
            if not recommendations:
                if strategy != 'popular':
                    messages.warning(request, f"使用{strategy}策略没有找到推荐，已切换到热门推荐")
                    return redirect(f"{request.path}?strategy=popular")
                else:
                    # 当热门推荐也失败时，获取任何动漫
                    messages.warning(request, "无法生成推荐，正在显示随机动漫")
                    animes = list(Anime.objects.all().order_by('?')[:limit])
                    context = {
                        'recommendations': animes,
                        'strategy': 'popular',
                        'strategies': get_strategy_list(),
                        'active_tab': 'recommendations'  # 添加active_tab
                    }
                    return render(request, 'recommendation/recommendations.html', context)

            # 获取推荐的动漫详情
            anime_ids = [rec[0] for rec in recommendations]
            recommended_animes = list(Anime.objects.filter(id__in=anime_ids))

            # 如果没有找到任何动漫，获取随机动漫
            if not recommended_animes:
                messages.warning(request, "找不到推荐的动漫，显示随机内容")
                recommended_animes = list(Anime.objects.all().order_by('?')[:limit])

            # 按推荐顺序排序
            id_to_anime = {anime.id: anime for anime in recommended_animes}
            sorted_animes = []
            for anime_id, score in recommendations:
                if anime_id in id_to_anime:
                    anime = id_to_anime[anime_id]
                    # 动态添加推荐置信度属性
                    anime.rec_score = round(score * 100)
                    sorted_animes.append(anime)

            # 如果排序后列表为空，使用原始列表
            if not sorted_animes:
                for anime in recommended_animes:
                    anime.rec_score = 50  # 默认置信度
                sorted_animes = recommended_animes

            # 分页处理
            paginator = Paginator(sorted_animes, limit)
            paged_animes = paginator.get_page(page)

            # 返回页面
            context = {
                'recommendations': paged_animes,
                'page_obj': paged_animes,
                'is_paginated': paginator.num_pages > 1,
                'strategy': strategy,
                'strategies': get_strategy_list(),
                'active_tab': 'recommendations'  # 添加active_tab
            }

            return render(request, 'recommendation/recommendations.html', context)

        except Exception as inner_e:
            # 内部异常处理：尝试显示随机动漫
            logger.error(f"推荐引擎异常: {str(inner_e)}")
            messages.error(request, "推荐引擎遇到问题，显示随机动漫")

            animes = list(Anime.objects.all().order_by('?')[:limit])
            if animes:
                for anime in animes:
                    anime.rec_score = 50  # 默认置信度

                context = {
                    'recommendations': animes,
                    'strategy': 'popular',
                    'strategies': get_strategy_list(),
                    'active_tab': 'recommendations'  # 添加active_tab
                }
                return render(request, 'recommendation/recommendations.html', context)
            else:
                # 如果没有任何动漫数据，显示错误页面
                raise Exception("数据库中没有动漫数据")

    except Exception as e:
        # 最外层异常处理：显示错误页面
        logger.error(f"致命错误: {str(e)}\n{traceback.format_exc()}")
        context = {
            'error_message': f'获取推荐时发生严重错误，请联系管理员。详情：{str(e)}',
            'active_tab': 'recommendations'  # 添加active_tab
        }
        return render(request, 'recommendation/recommendation_error.html', context)


@login_required
def browsing_history(request):
    """
    浏览历史页面
    显示用户的动漫浏览历史记录
    """
    try:
        # 获取用户的浏览历史记录，按最近浏览时间排序
        history_list = UserBrowsing.objects.filter(
            user=request.user
        ).select_related('anime').order_by('-last_browsed')

        # 分页处理
        paginator = Paginator(history_list, 10)  # 每页10条记录
        page = request.GET.get('page', 1)

        try:
            browsing_history = paginator.page(page)
        except:
            browsing_history = paginator.page(1)

        context = {
            'browsing_history': browsing_history,
            'is_paginated': paginator.num_pages > 1,
            'page_obj': browsing_history,
            'active_tab': 'history'  # 添加active_tab
        }

        return render(request, 'recommendation/browsing_history.html', context)
    except Exception as e:
        logger.error(f"浏览历史页面加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载浏览历史时出错，请稍后再试")
        return redirect('anime:anime_list')


@login_required
# 在views.py文件中
def user_favorites(request):
    """
    用户收藏页面
    显示用户收藏的动漫列表
    """
    try:
        # 获取用户的收藏列表
        favorites_list = UserFavorite.objects.filter(
            user=request.user
        ).select_related('anime').order_by('-timestamp')

        # 分页处理
        paginator = Paginator(favorites_list, 6)  # 这里设置的是12而不是6
        page = request.GET.get('page', 1)

        try:
            favorites = paginator.page(page)
        except:
            favorites = paginator.page(1)

        context = {
            'favorites': favorites,
            'is_paginated': paginator.num_pages > 1,
            'page_obj': favorites,
            'active_tab': 'favorites'
        }

        return render(request, 'recommendation/favorites.html', context)
    except Exception as e:
        logger.error(f"收藏页面加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载收藏列表时出错，请稍后再试")
        return redirect('anime:anime_list')


@login_required
def user_comments(request):
    """
    用户评论列表页面
    显示当前用户发表的所有评论
    """
    try:
        # 获取用户的所有评论，按时间倒序排列
        comments_list = UserComment.objects.filter(
            user=request.user
        ).select_related('anime').order_by('-timestamp')

        # 分页处理
        paginator = Paginator(comments_list, 10)  # 每页10条记录
        page = request.GET.get('page', 1)

        try:
            comments = paginator.page(page)
        except:
            comments = paginator.page(1)

        context = {
            'comments': comments,
            'is_paginated': paginator.num_pages > 1,
            'page_obj': comments,
            'active_tab': 'comments'  # 添加active_tab
        }

        return render(request, 'recommendation/user_comments.html', context)
    except Exception as e:
        logger.error(f"评论页面加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载评论列表时出错，请稍后再试")
        return redirect('anime:anime_list')
# recommendation/views.py 中修改以下视图函数

@login_required
def dashboard_likes_api(request):
    """
    仪表板点赞API
    返回用户的动漫点赞记录
    """
    try:
        user = request.user
        from recommendation.models import AnimeLike
        # 获取用户最近的动漫点赞记录
        likes = AnimeLike.objects.filter(user=user).select_related('anime').order_by('-timestamp')[:5]

        # 构建返回数据
        result = []
        for like in likes:
            result.append({
                'id': like.id,
                'animeId': like.anime.id,
                'animeSlug': like.anime.slug,
                'animeTitle': like.anime.title,
                'date': like.timestamp.strftime('%Y-%m-%d %H:%M'),
                'coverUrl': request.build_absolute_uri(like.anime.cover.url) if like.anime.cover else None
            })

        return JsonResponse({
            'success': True,
            'likes': result
        })
    except Exception as e:
        logger.error(f"获取点赞记录失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取点赞记录失败: {str(e)}'
        }, status=500)
@login_required
def user_likes(request):
    """
    用户点赞记录页面
    显示用户点赞过的所有动漫
    """
    try:
        from recommendation.models import AnimeLike
        user = request.user
        likes_list = AnimeLike.objects.filter(user=user).select_related('anime').order_by('-timestamp')

        # 分页
        paginator = Paginator(likes_list, 12)  # 每页12条记录
        page = request.GET.get('page')

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        context = {
            'likes': page_obj,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'active_tab': 'likes'  # 用于导航栏高亮
        }

        return render(request, 'recommendation/user_likes.html', context)
    except Exception as e:
        logger.error(f"点赞页面加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载点赞列表时出错，请稍后再试")
        return redirect('anime:anime_list')
@login_required
def user_activity_dashboard(request):
    """
    用户活动仪表板
    展示用户的评分、评论、点赞和推荐历史
    """
    try:
        # 获取用户评分数据
        user_ratings = UserRating.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:10]

        # 获取用户评论数据
        user_comments = UserComment.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[
                        :10]

        # 转换为JSON格式，用于前端渲染
        ratings_data = []
        for rating in user_ratings:
            ratings_data.append({
                'animeId': rating.anime.id,
                'animeTitle': rating.anime.title,
                'animeSlug': rating.anime.slug,
                'rating': float(rating.rating),
                'date': rating.timestamp.strftime('%Y-%m-%d')
            })

        comments_data = []
        for comment in user_comments:
            comments_data.append({
                'animeId': comment.anime.id,
                'animeTitle': comment.anime.title,
                'animeSlug': comment.anime.slug,
                'content': comment.content,
                'date': comment.timestamp.strftime('%Y-%m-%d %H:%M'),
                'like_count': comment.like_count,
                'commentId': comment.id
            })

        # 获取用户动漫点赞数据
        from recommendation.models import AnimeLike
        likes_data = []

        try:
            # 使用更明确的错误处理
            user_likes = AnimeLike.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:5]

            for like in user_likes:
                likes_data.append({
                    'id': like.id,
                    'animeId': like.anime.id,
                    'animeSlug': like.anime.slug,
                    'animeTitle': like.anime.title,
                    'date': like.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'coverUrl': request.build_absolute_uri(like.anime.cover.url) if like.anime.cover else None
                })
        except Exception as like_error:
            # 记录点赞数据获取失败，但不中断整个仪表盘
            logger.error(f"获取用户点赞数据失败: {str(like_error)}\n{traceback.format_exc()}")
            # 设置空的点赞数据
            likes_data = []

        # 获取默认推荐
        try:
            initial_recommendations = recommendation_engine.get_recommendations_for_user(request.user.id, limit=6)
            anime_ids = [rec[0] for rec in initial_recommendations]
            animes = list(Anime.objects.filter(id__in=anime_ids))

            # 按推荐顺序排序
            id_to_anime = {anime.id: anime for anime in animes}
            sorted_recommendations = []
            for anime_id, score in initial_recommendations:
                if anime_id in id_to_anime:
                    anime = id_to_anime[anime_id]
                    anime.confidence = round(score * 100)
                    sorted_recommendations.append(anime)
        except Exception as e:
            logger.error(f"获取初始推荐失败: {str(e)}")
            sorted_recommendations = []

        context = {
            'user_ratings': json.dumps(ratings_data),
            'user_comments': json.dumps(comments_data),
            'user_likes': json.dumps(likes_data),
            'recommendations': sorted_recommendations,
            'strategies': get_strategy_list(),
            'active_tab': 'dashboard'
        }

        return render(request, 'recommendation/user_dashboard.html', context)
    except Exception as e:
        logger.error(f"仪表板加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载仪表板数据时出错，请稍后再试")
        return redirect('anime:anime_list')
# 对RecommendationAPIView进行增强，支持分页信息返回

class RecommendationAPIView(APIView):
    """
    推荐API端点 - 量子分页增强版
    提供JSON格式的推荐结果，包含完整分页信息
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 获取请求参数
        strategy = request.query_params.get('strategy', 'hybrid')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 12))

        # 验证参数
        if strategy not in ['hybrid', 'cf', 'content', 'popular', 'ml']:
            strategy = 'hybrid'

        if limit > 50:
            limit = 50  # 限制最大结果数

        if page < 1:
            page = 1

        try:
            # 检查GBDT模型文件是否存在
            if strategy == 'ml':
                model_path = os.path.join('recommendation', 'engine', 'models', 'gbdt_model.joblib')
                encoders_path = os.path.join('recommendation', 'engine', 'models', 'gbdt_encoders.pkl')

                if not (os.path.exists(model_path) and os.path.exists(encoders_path)):
                    return Response({
                        'success': False,
                        'error': 'GBDT模型文件不存在',
                        'message': '请确保模型文件已正确训练和保存'
                    }, status=status.HTTP_404_NOT_FOUND)

            # 获取推荐结果
            user_id = request.user.id
            recommendations = recommendation_engine.get_recommendations_for_user(
                user_id, limit=limit * 2, strategy=strategy
            )

            # 获取推荐的动漫详情
            anime_ids = [rec[0] for rec in recommendations]
            anime_dict = {anime.id: anime for anime in Anime.objects.filter(id__in=anime_ids)}

            # 构建响应数据
            result = []
            for anime_id, score in recommendations:
                if anime_id in anime_dict:
                    anime = anime_dict[anime_id]
                    result.append({
                        'id': anime.id,
                        'title': anime.title,
                        'cover_url': request.build_absolute_uri(anime.cover.url) if anime.cover else None,
                        'rating': anime.rating_avg,
                        'score': round(score * 100),  # 转换为百分比
                        'url': request.build_absolute_uri(f'/anime/{anime.slug}/')
                    })

            # 计算分页信息
            total_items = len(result)
            total_pages = (total_items + limit - 1) // limit  # 向上取整

            # 分页切片
            start = (page - 1) * limit
            end = min(start + limit, total_items)
            paged_results = result[start:end]

            return Response({
                'success': True,
                'strategy': strategy,
                'recommendations': paged_results,
                'pagination': {
                    'current_page': page,
                    'total_pages': max(1, total_pages),  # 至少1页
                    'total_items': total_items,
                    'items_per_page': limit,
                    'has_next': page < total_pages,
                    'has_previous': page > 1
                },
                'strategy_name': {
                    'hybrid': '混合推荐',
                    'cf': '协同过滤',
                    'content': '基于内容',
                    'ml': '基于GBDT',
                    'popular': '热门推荐'
                }.get(strategy, '未知策略')
            })

        except Exception as e:
            logger.error(f"推荐API错误: {str(e)}\n{traceback.format_exc()}")
            return Response({
                'success': False,
                'error': '获取推荐失败',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@login_required
@require_POST
def remove_history(request, history_id):
    """
    移除单条浏览历史记录
    """
    try:
        history = get_object_or_404(UserBrowsing, id=history_id, user=request.user)
        history.delete()

        return JsonResponse({
            'success': True,
            'message': '已从浏览历史中移除'
        })
    except Exception as e:
        logger.error(f"移除浏览历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '移除历史记录失败'
        }, status=400)


@login_required
@require_POST
def clear_history(request):
    """
    清空用户的所有浏览历史
    """
    try:
        UserBrowsing.objects.filter(user=request.user).delete()

        return JsonResponse({
            'success': True,
            'message': '已清空所有浏览历史'
        })
    except Exception as e:
        logger.error(f"清空浏览历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '清空历史记录失败'
        }, status=400)


@login_required
def dashboard_seasonal_api(request):
    """
    仪表板季节性动漫API - 量子级自适应版
    支持多级降级策略确保数据非空
    """
    try:
        # ===== Tier-1: 严格三个月时间窗口 =====
        three_months_ago = timezone.now() - timedelta(days=90)
        seasonal_anime = Anime.objects.filter(
            release_date__gte=three_months_ago
        ).order_by('-release_date')[:4]

        # ===== Tier-2: 降级到六个月时间窗口 =====
        if not seasonal_anime.exists():
            logger.info("[QUANTUM] 三个月窗口无数据，扩展到六个月")
            six_months_ago = timezone.now() - timedelta(days=180)
            seasonal_anime = Anime.objects.filter(
                release_date__gte=six_months_ago
            ).order_by('-release_date')[:4]

        # ===== Tier-3: 降级到十二个月时间窗口 =====
        if not seasonal_anime.exists():
            logger.info("[QUANTUM] 六个月窗口无数据，扩展到十二个月")
            one_year_ago = timezone.now() - timedelta(days=365)
            seasonal_anime = Anime.objects.filter(
                release_date__gte=one_year_ago
            ).order_by('-release_date')[:4]

        # ===== 兜底策略: 返回任何最新动漫 =====
        if not seasonal_anime.exists():
            logger.warning("[QUANTUM] 所有时间窗口皆无数据，切换到无约束模式")
            seasonal_anime = Anime.objects.all().order_by('-release_date')[:4]

        # 构建响应数据
        result = []
        for anime in seasonal_anime:
            result.append({
                'id': anime.id,
                'title': anime.title,
                'image': request.build_absolute_uri(anime.cover.url) if anime.cover else None,
                'slug': anime.slug,
                'type': anime.type.name if anime.type else None,
                'release_date': anime.release_date.strftime('%Y-%m-%d') if anime.release_date else None
            })

        return JsonResponse({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"[QUANTUM-ERROR] 季节性动漫API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f'获取季节性动漫失败: {str(e)}'}, status=500)


@login_required
def dashboard_similar_api(request):
    """
    仪表板相似动漫API - 量子级错误处理版
    解决推荐引擎接口不匹配问题，实现多层降级策略
    """
    try:
        user = request.user

        # ===== 获取用户评分数据 - 检测空集情况 =====
        top_rated = UserRating.objects.filter(
            user=user
        ).order_by('-rating')[:2]  # 获取评分最高的2部动漫

        if not top_rated.exists():
            # 如果用户没有评分任何动漫，返回明确信息
            logger.info(f"[QUANTUM] 用户{user.id}没有评分记录，无法生成相似推荐")
            return JsonResponse({
                'success': True,
                'reference_anime': [],
                'data': []
            })

        # 获取用户高评分的动漫ID
        top_anime_ids = [rating.anime.id for rating in top_rated]
        top_anime = [rating.anime for rating in top_rated]

        # 用户高评分动漫的引用信息
        reference_anime = [{
            'id': anime.id,
            'title': anime.title,
            'slug': anime.slug
        } for anime in top_anime]

        # ===== 核心逻辑改进: 多策略推荐获取 =====
        # 使用基于内容的推荐获取相似动漫
        similar_anime_ids = set()
        for anime_id in top_anime_ids:
            try:
                # 策略1: 尝试使用seed_anime_id参数 (如果支持)
                try:
                    similar_recommendations = recommendation_engine.get_recommendations_for_user(
                        user.id,
                        limit=4,
                        strategy='content',
                    )
                    for rec_id, _ in similar_recommendations:
                        similar_anime_ids.add(rec_id)
                except TypeError as e:
                    # 策略2: seed_anime_id不被支持，使用普通内容推荐
                    logger.info(f"[QUANTUM] 引擎不支持seed_anime_id参数: {str(e)}")
                    similar_recommendations = recommendation_engine.get_recommendations_for_user(
                        user.id, limit=4, strategy='content'
                    )
                    for rec_id, _ in similar_recommendations:
                        similar_anime_ids.add(rec_id)
            except Exception as e:
                # 策略3: 推荐引擎异常，使用基于类型的简单相似性
                logger.warning(f"[QUANTUM] 推荐引擎异常: {str(e)}, 切换到类型匹配")
                try:
                    anime = Anime.objects.get(id=anime_id)
                    if anime.type:
                        similar_by_type = Anime.objects.filter(
                            type=anime.type
                        ).exclude(id=anime_id).order_by('-rating_avg')[:4]
                        for similar in similar_by_type:
                            similar_anime_ids.add(similar.id)
                except Exception as inner_e:
                    logger.error(f"[QUANTUM] 类型匹配也失败: {str(inner_e)}")
                    # 继续尝试下一个anime_id

        # ===== 兜底策略1: 基于类型匹配 =====
        if not similar_anime_ids:
            logger.warning("[QUANTUM] 无法获取相似推荐，使用类型匹配降级策略")
            type_ids = []
            for anime in top_anime:
                if anime.type:
                    type_ids.append(anime.type.id)

            if type_ids:
                similar_by_type = Anime.objects.filter(
                    type__id__in=type_ids
                ).exclude(id__in=top_anime_ids).order_by('-rating_avg')[:4]

                similar_anime_ids = {anime.id for anime in similar_by_type}

        # ===== 兜底策略2: 返回热门动漫 =====
        if not similar_anime_ids:
            logger.warning("[QUANTUM] 类型匹配也无结果，返回热门动漫")
            popular_anime = Anime.objects.all().order_by('-popularity')[:4]
            similar_anime_ids = {anime.id for anime in popular_anime}

        # 移除用户已评分的动漫
        user_rated_ids = set(UserRating.objects.filter(user=user).values_list('anime_id', flat=True))
        similar_anime_ids = similar_anime_ids - user_rated_ids - set(top_anime_ids)

        # 如果经过筛选后没有推荐，使用热门推荐
        if not similar_anime_ids:
            logger.warning("[QUANTUM] 过滤后无推荐，使用热门推荐兜底")
            popular_anime = Anime.objects.all().order_by('-popularity')[:4]
            similar_anime_ids = {anime.id for anime in popular_anime}

        # 获取动漫对象
        similar_anime = Anime.objects.filter(id__in=similar_anime_ids)[:4]

        # 构建响应
        result = []
        for anime in similar_anime:
            result.append({
                'id': anime.id,
                'title': anime.title,
                'image': request.build_absolute_uri(anime.cover.url) if anime.cover else None,
                'slug': anime.slug,
                'type': anime.type.name if anime.type else None
            })

        return JsonResponse({
            'success': True,
            'reference_anime': reference_anime,
            'data': result
        })
    except Exception as e:
        logger.error(f"[QUANTUM-ERROR] 相似动漫API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f'获取相似动漫失败: {str(e)}'}, status=500)


@login_required
def dashboard_classics_api(request):
    """
    仪表板经典动漫API - 量子级自适应版
    采用渐进式条件松弛确保非空响应
    """
    try:
        # ===== Tier-1: 严格高标准 (评分≥4.5, 评分数≥50) =====
        classics = Anime.objects.filter(
            rating_avg__gte=4.5,  # 高评分
            rating_count__gte=50  # 有显著数量的评分
        ).order_by('-rating_avg')[:4]  # 限制为8个

        # ===== Tier-2: 中等标准 (评分≥4.0, 评分数≥20) =====
        if not classics.exists():
            logger.info("[QUANTUM] 严格标准无匹配，降级到中等标准")
            classics = Anime.objects.filter(
                rating_avg__gte=4.0,
                rating_count__gte=20
            ).order_by('-rating_avg')[:4]

        # ===== Tier-3: 宽松标准 (评分≥3.5, 评分数≥5) =====
        if not classics.exists():
            logger.info("[QUANTUM] 中等标准无匹配，降级到宽松标准")
            classics = Anime.objects.filter(
                rating_avg__gte=3.5,
                rating_count__gte=5
            ).order_by('-rating_avg')[:4]

        # ===== 兜底策略: 返回任何评分最高的动漫 =====
        if not classics.exists():
            logger.warning("[QUANTUM] 所有评分标准皆无匹配，切换到无约束模式")
            classics = Anime.objects.all().order_by('-rating_avg')[:4]

        # 构建响应
        result = []
        for anime in classics:
            result.append({
                'id': anime.id,
                'title': anime.title,
                'image': request.build_absolute_uri(anime.cover.url) if anime.cover else None,
                'slug': anime.slug,
                'type': anime.type.name if anime.type else None,
                'rating': anime.rating_avg
            })

        return JsonResponse({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"[QUANTUM-ERROR] 经典动漫API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f'获取经典动漫失败: {str(e)}'}, status=500)
@login_required
@require_POST
def add_comment(request, anime_id):
    """
    添加评论API
    """
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        data = json.loads(request.body)
        content = data.get('content', '').strip()

        if not content:
            return JsonResponse({
                'success': False,
                'error': '评论内容不能为空'
            }, status=400)

        # 创建新评论
        comment = UserComment.objects.create(
            user=request.user,
            anime=anime,
            content=content
        )

        # 返回新评论的基本信息，用于前端显示
        return JsonResponse({
            'success': True,
            'message': '评论发表成功',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M'),
                'user': {
                    'username': request.user.username,
                    'avatar': request.user.profile.avatar.url if request.user.profile.avatar else None
                },
                'like_count': 0
            }
        })
    except Exception as e:
        logger.error(f"添加评论失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '评论发表失败，请稍后再试'
        }, status=500)


@login_required
@require_POST
def update_comment(request, comment_id):
    """
    更新评论API
    """
    try:
        comment = get_object_or_404(UserComment, id=comment_id, user=request.user)
        data = json.loads(request.body)
        content = data.get('content', '').strip()

        if not content:
            return JsonResponse({
                'success': False,
                'error': '评论内容不能为空'
            }, status=400)

        # 更新评论内容
        comment.content = content
        comment.save(update_fields=['content'])

        return JsonResponse({
            'success': True,
            'message': '评论更新成功',
            'content': comment.content
        })
    except Exception as e:
        logger.error(f"更新评论失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '评论更新失败，请稍后再试'
        }, status=500)


@login_required
@require_POST
def delete_comment(request, comment_id):
    """
    删除评论API
    """
    try:
        comment = get_object_or_404(UserComment, id=comment_id, user=request.user)
        comment.delete()

        # 更新用户评论计数
        if request.user.profile.comment_count > 0:
            request.user.profile.comment_count -= 1
            request.user.profile.save(update_fields=['comment_count'])

        return JsonResponse({
            'success': True,
            'message': '评论已删除'
        })
    except Exception as e:
        logger.error(f"删除评论失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '删除评论失败，请稍后再试'
        }, status=500)

@login_required
@require_POST
def heart_rating(request, anime_id):
    """
    心形评分系统API
    """
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        data = json.loads(request.body)
        rating = float(data.get('rating', 0))

        # 验证评分值（1-5）
        if rating < 1 or rating > 5:
            return JsonResponse({
                'success': False,
                'error': '评分必须在1到5之间'
            }, status=400)

        # 更新或创建评分
        was_new = False
        try:
            user_rating = UserRating.objects.get(user=request.user, anime=anime)
            old_rating = user_rating.rating
            user_rating.rating = rating
            user_rating.save(update_fields=['rating', 'timestamp'])
        except UserRating.DoesNotExist:
            UserRating.objects.create(
                user=request.user,
                anime=anime,
                rating=rating
            )
            was_new = True
            old_rating = 0

        # 计算并更新动漫的平均评分
        from django.db.models import Avg
        new_avg = UserRating.objects.filter(anime=anime).aggregate(Avg('rating'))['rating__avg'] or 0

        anime.rating_avg = new_avg
        anime.save(update_fields=['rating_avg'])

        # 返回更新后的信息
        return JsonResponse({
            'success': True,
            'message': '评分已提交',
            'rating': rating,
            'was_new': was_new,
            'old_rating': old_rating,
            'new_avg': round(new_avg, 1)
        })
    except Exception as e:
        logger.error(f"心形评分失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '评分失败，请稍后再试'
        }, status=500)


# ========================= 仪表板 API 端点 =========================

@login_required
def dashboard_recommendations_api(request):
    """
    仪表板推荐API
    """
    try:
        strategy = request.GET.get('strategy', 'hybrid')
        limit = int(request.GET.get('limit', 6))

        # 验证参数
        valid_strategies = ['hybrid', 'cf', 'content', 'popular', 'ml']
        if strategy not in valid_strategies:
            strategy = 'hybrid'

        if limit > 20:
            limit = 20

        # 获取推荐
        recommendations = recommendation_engine.get_recommendations_for_user(
            request.user.id, limit=limit, strategy=strategy
        )

        # 获取动漫详情
        anime_ids = [rec[0] for rec in recommendations]
        animes = Anime.objects.filter(id__in=anime_ids)

        # 构建响应数据
        result = []
        for anime_id, score in recommendations:
            anime = next((a for a in animes if a.id == anime_id), None)
            if anime:
                result.append({
                    'id': anime.id,
                    'title': anime.title,
                    'image': request.build_absolute_uri(anime.cover.url) if anime.cover else None,
                    'confidence': round(score * 100),
                    'url': f"/anime/{anime.slug}/"
                })

        return JsonResponse({'success': True, 'recommendations': result})
    except Exception as e:
        logger.error(f"仪表板推荐API错误: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def dashboard_ratings_api(request):
    """
    仪表盘评分API
    """
    try:
        # 获取用户评分
        user_ratings = UserRating.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:10]

        # 构建响应数据
        ratings = []
        for rating in user_ratings:
            ratings.append({
                'animeId': rating.anime.id,
                'animeTitle': rating.anime.title,
                'animeSlug': rating.anime.slug,  # 添加slug字段
                'rating': float(rating.rating),
                'date': rating.timestamp.strftime('%Y-%m-%d %H:%M'),
                'ratingId': rating.id  # 可选：添加评分ID
            })

        return JsonResponse({'success': True, 'ratings': ratings})
    except Exception as e:
        logger.error(f"仪表盘评分API错误: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def dashboard_comments_api(request):
    """
    仪表板评论API
    """
    try:
        # 获取用户评论
        user_comments = UserComment.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:10]

        # 构建响应数据
        comments = []
        for comment in user_comments:
            comments.append({
                'animeId': comment.anime.id,
                'animeTitle': comment.anime.title,
                'animeSlug': comment.anime.slug,
                'content': comment.content,
                'date': comment.timestamp.strftime('%Y-%m-%d %H:%M'),
                'like_count': comment.like_count,
                'commentId': comment.id
            })

        return JsonResponse({'success': True, 'comments': comments})
    except Exception as e:
        logger.error(f"仪表板评论API错误: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================= 辅助函数 =========================

def get_strategy_list():
    """
    获取推荐策略列表
    """
    return [
        {'code': 'hybrid', 'name': '混合推荐', 'icon': 'fa-magic', 'desc': '结合多种算法的综合推荐'},
        {'code': 'cf', 'name': '协同过滤', 'icon': 'fa-users', 'desc': '基于相似用户喜好的推荐'},
        {'code': 'content', 'name': '基于内容', 'icon': 'fa-tags', 'desc': '根据动漫特征相似度推荐'},
        {'code': 'ml', 'name': '基于GBDT', 'icon': 'fa-brain', 'desc': '使用梯度提升决策树算法的推荐'},
        {'code': 'popular', 'name': '热门推荐', 'icon': 'fa-fire', 'desc': '当前最热门的动漫'}
    ]


# recommendation/views.py 中添加的数据可视化API端点

from django.db.models import Count, Sum, Case, When, F, Value, IntegerField
from django.db.models.functions import TruncDate, Coalesce
from django.utils import timezone
from datetime import timedelta
import random
@login_required
def user_likes(request):
    """
    用户点赞记录视图：展示用户所有点赞过的动漫
    - 按时间倒序排列
    - 支持分页
    """
    try:
        from recommendation.models import AnimeLike
        user = request.user
        likes_list = AnimeLike.objects.filter(user=user).select_related('anime').order_by('-timestamp')

        # 分页
        paginator = Paginator(likes_list, 12)  # 每页12条记录
        page = request.GET.get('page')

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        context = {
            'likes': page_obj,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'active_tab': 'likes'  # 用于导航栏高亮
        }

        return render(request, 'recommendation/user_likes.html', context)
    except Exception as e:
        logger.error(f"点赞页面加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载点赞列表时出错，请稍后再试")
        return redirect('anime:anime_list')

@login_required
def visualization_genre_preference(request):
    """
    类型偏好分析API
    基于用户的浏览、评分和收藏记录，分析用户的动漫类型偏好
    """
    try:
        user = request.user

        # 获取用户评分过的动漫的类型
        rated_anime_types = UserRating.objects.filter(user=user).select_related('anime__type')
        type_data = {}

        # 统计每个类型的评分情况
        for rating in rated_anime_types:
            type_name = rating.anime.type.name
            if type_name not in type_data:
                type_data[type_name] = {
                    'rating_count': 0,
                    'total_rating': 0,
                    'browse_count': 0,
                    'favorite_count': 0
                }
            type_data[type_name]['rating_count'] += 1
            type_data[type_name]['total_rating'] += rating.rating

        # 获取用户浏览记录中的动漫类型
        browsed_anime_types = UserBrowsing.objects.filter(user=user).select_related('anime__type')
        for browsing in browsed_anime_types:
            type_name = browsing.anime.type.name
            if type_name not in type_data:
                type_data[type_name] = {
                    'rating_count': 0,
                    'total_rating': 0,
                    'browse_count': 0,
                    'favorite_count': 0
                }
            type_data[type_name]['browse_count'] += browsing.browse_count

        # 获取用户收藏的动漫类型
        favorite_anime_types = UserFavorite.objects.filter(user=user).select_related('anime__type')
        for favorite in favorite_anime_types:
            type_name = favorite.anime.type.name
            if type_name not in type_data:
                type_data[type_name] = {
                    'rating_count': 0,
                    'total_rating': 0,
                    'browse_count': 0,
                    'favorite_count': 0
                }
            type_data[type_name]['favorite_count'] += 1

        # 计算每个类型的偏好分数
        preference_scores = []
        for type_name, data in type_data.items():
            # 偏好分数计算逻辑：评分权重 * 平均评分 + 浏览权重 * 浏览次数 + 收藏权重 * 收藏次数
            avg_rating = data['total_rating'] / data['rating_count'] if data['rating_count'] > 0 else 0

            # 权重设置
            rating_weight = 2.0
            browse_weight = 0.2
            favorite_weight = 3.0

            # 计算偏好分数
            preference_score = (
                    rating_weight * avg_rating * data['rating_count'] +
                    browse_weight * data['browse_count'] +
                    favorite_weight * data['favorite_count']
            )

            preference_scores.append({
                'name': type_name,
                'value': round(preference_score, 2)
            })

        # 按偏好分数降序排序
        preference_scores.sort(key=lambda x: x['value'], reverse=True)

        # 取前8个类型
        top_preferences = preference_scores[:8]

        return JsonResponse({
            'success': True,
            'data': top_preferences
        })
    except Exception as e:
        logger.error(f"类型偏好数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取类型偏好数据失败: {str(e)}'
        }, status=500)


@login_required
def visualization_rating_distribution(request):
    """
    评分分布分析API
    分析用户的评分分布情况，展示不同评分分数的分布
    """
    try:
        user = request.user

        # 获取用户的评分记录
        ratings = UserRating.objects.filter(user=user)

        # 如果没有评分记录
        if not ratings.exists():
            # 返回空数据
            return JsonResponse({
                'success': True,
                'data': []
            })

        # 统计每个评分的次数
        rating_distribution = {}
        for r in range(1, 6):  # 1-5分
            # 计算四舍五入到每个整数分数的评分数量
            count = ratings.filter(rating__gte=r - 0.25, rating__lt=r + 0.75).count()
            rating_distribution[r] = count

        # 构建数据
        data = [
            {'rating': r, 'count': rating_distribution[r]}
            for r in range(1, 6)
        ]

        return JsonResponse({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"评分分布数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取评分分布数据失败: {str(e)}'
        }, status=500)

@login_required
def visualization_viewing_trends(request):
    """
    观看趋势分析API
    分析用户近期的活跃度趋势，包括浏览量和评分频率
    """
    try:
        user = request.user

        # 获取过去14天的日期范围
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=13)
        date_range = [start_date + timedelta(days=i) for i in range(14)]

        # 查询用户在这段时间内的浏览记录
        browsing_data = (
            UserBrowsing.objects
            .filter(
                user=user,
                last_browsed__date__gte=start_date,
                last_browsed__date__lte=end_date
            )
            .annotate(date=TruncDate('last_browsed'))
            .values('date')
            .annotate(views=Count('id'))
            .order_by('date')
        )

        # 查询用户在这段时间内的评分记录
        rating_data = (
            UserRating.objects
            .filter(
                user=user,
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(ratings=Count('id'))
            .order_by('date')
        )

        # 将查询结果转换为字典，以日期为键
        browsing_dict = {item['date'].isoformat(): item['views'] for item in browsing_data}
        rating_dict = {item['date'].isoformat(): item['ratings'] for item in rating_data}

        # 构建完整的日期序列数据
        result = []
        for d in date_range:
            date_str = d.isoformat()
            result.append({
                'date': date_str,
                'views': browsing_dict.get(date_str, 0),
                'ratings': rating_dict.get(date_str, 0)
            })

        return JsonResponse({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"观看趋势数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取观看趋势数据失败: {str(e)}'
        }, status=500)


# recommendation/views.py 中添加的数据可视化API端点

from django.db.models import Count, Sum, Case, When, F, Value, IntegerField
from django.db.models.functions import TruncDate, Coalesce
from django.utils import timezone
from datetime import timedelta
import random


# ========================= 数据可视化 API 端点 =========================

@login_required
def visualization_user_activity(request):
    """
    用户活动分析API
    返回用户在系统中的活动分布数据（浏览、评分、评论、收藏）
    """
    try:
        user = request.user

        # 获取用户的浏览记录数
        browsing_count = UserBrowsing.objects.filter(user=user).count()

        # 获取用户的评分记录数
        rating_count = UserRating.objects.filter(user=user).count()

        # 获取用户的评论记录数
        comment_count = UserComment.objects.filter(user=user).count()

        # 获取用户的收藏记录数
        favorite_count = UserFavorite.objects.filter(user=user).count()

        # 构建数据
        data = [
            {
                'name': '浏览记录',
                'value': browsing_count,
                'color': '#6d28d9'  # 紫色
            },
            {
                'name': '评分记录',
                'value': rating_count,
                'color': '#10b981'  # 绿色
            },
            {
                'name': '评论记录',
                'value': comment_count,
                'color': '#f97316'  # 橙色
            },
            {
                'name': '收藏记录',
                'value': favorite_count,
                'color': '#2563eb'  # 蓝色
            }
        ]

        return JsonResponse({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"用户活动数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取活动数据失败: {str(e)}'
        }, status=500)
@login_required
def user_ratings(request):
    """用户评分历史页面"""
    user_ratings = UserRating.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')

    return render(request, 'recommendation/user_ratings.html', {
        'user_ratings': user_ratings,
        'active_tab': 'dashboard'
    })


# 在views.py文件中的favorites视图函数中
from django.core.paginator import Paginator


def favorites_view(request):
    user_favorites = UserFavorite.objects.filter(user=request.user).order_by('-timestamp')

    # 将每页项目数从默认值修改为6
    paginator = Paginator(user_favorites, 6)  # 这里设置为6个

    page = request.GET.get('page')
    favorites = paginator.get_page(page)

    return render(request, 'recommendation/favorites.html', {'favorites': favorites})

@login_required
@require_POST
def toggle_favorite(request, anime_id):
    """
    收藏切换API：处理添加/移除收藏操作
    支持幂等操作 - 重复请求会产生相同结果
    """
    try:
        anime = get_object_or_404(Anime, id=anime_id)

        # 检查是否已经收藏
        favorite = UserFavorite.objects.filter(user=request.user, anime=anime).first()

        if favorite:
            # 已收藏，执行移除
            favorite.delete()
            logger.info(f"用户 {request.user.id} 取消收藏动漫 {anime_id}")

            return JsonResponse({
                'success': True,
                'action': 'removed',
                'message': '已从收藏中移除'
            })
        else:
            # 未收藏，添加收藏
            UserFavorite.objects.create(user=request.user, anime=anime)
            logger.info(f"用户 {request.user.id} 添加收藏动漫 {anime_id}")

            return JsonResponse({
                'success': True,
                'action': 'added',
                'message': '已添加到收藏'
            })
    except Exception as e:
        logger.error(f"收藏操作失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': '操作失败，请稍后再试'
        }, status=500)


# 用户互动页面视图
@login_required
def user_interactions(request):
    """
    用户互动页面：展示用户之间的互动数据，包括评论回复、点赞等
    """
    try:
        # 获取基本统计
        interaction_stats = {
            'total_interactions': UserInteraction.objects.count(),
            'latest_interactions': UserInteraction.objects.order_by('-timestamp')[:5],
        }

        context = {
            'page_title': '用户互动',
            'interaction_stats': interaction_stats
        }

        return render(request, 'recommendation/user_interactions.html', context)
    except Exception as e:
        logger.error(f"用户互动页面异常: {str(e)}\n{traceback.format_exc()}")
        return redirect('recommendation:recommendations')


# 用户互动网络可视化页面
@login_required
def user_interaction_network(request):
    """
    用户互动网络可视化页面：展示用户之间的互动关系网络图
    """
    try:
        context = {
            'page_title': '互动网络',
        }
        return render(request, 'recommendation/user_interaction_network.html', context)
    except Exception as e:
        logger.error(f"用户互动网络页面异常: {str(e)}\n{traceback.format_exc()}")
        return redirect('recommendation:user_interactions')


# 添加评论回复API
@login_required
@require_POST
def add_comment_reply(request, comment_id):
    """
    添加评论回复API：处理用户对评论的回复
    """
    try:
        # 获取父评论
        parent_comment = get_object_or_404(UserComment, id=comment_id)

        # 解析请求数据
        data = json.loads(request.body)
        content = data.get('content', '').strip()

        # 验证内容
        if not content:
            return JsonResponse({
                'success': False,
                'error': '回复内容不能为空'
            }, status=400)

        # 创建新回复
        reply = UserComment.objects.create(
            user=request.user,
            anime=parent_comment.anime,
            content=content,
            is_reply=True,
            parent_comment=parent_comment
        )

        # 更新父评论的回复计数
        parent_comment.reply_count = UserComment.objects.filter(parent_comment=parent_comment).count()
        parent_comment.save(update_fields=['reply_count'])

        # 创建互动记录
        UserInteraction.objects.create(
            from_user=request.user,
            to_user=parent_comment.user,
            interaction_type='reply',
            comment=reply,
            strength=1.2  # 回复互动强度较高
        )

        # 返回成功响应
        return JsonResponse({
            'success': True,
            'reply_id': reply.id,
            'reply_count': parent_comment.reply_count,
            'message': '回复已提交'
        })
    except Exception as e:
        logger.error(f"添加评论回复失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': '添加回复失败，请稍后再试'
        }, status=500)


# 获取评论回复API
@require_GET
def get_comment_replies(request, comment_id):
    """
    获取评论回复API：获取某个评论下的所有回复
    """
    try:
        # 获取父评论
        parent_comment = get_object_or_404(UserComment, id=comment_id)

        # 获取回复列表
        replies = UserComment.objects.filter(parent_comment=parent_comment).order_by('timestamp')

        # 为登录用户获取点赞信息
        user_likes = {}
        if request.user.is_authenticated:
            user_likes = {
                like.comment_id: True for like in UserLike.objects.filter(
                    user=request.user,
                    comment__in=replies
                )
            }

        # 渲染回复HTML
        replies_html = ""
        for reply in replies:
            # 针对每个回复，判断当前用户是否已点赞
            user_liked = user_likes.get(reply.id, False)

            # 使用评论模板渲染每条回复
            reply_html = render_to_string('recommendation/partials/comment.html', {
                'comment': reply,
                'user': request.user,
                'user_liked': user_liked
            })

            replies_html += reply_html

        return JsonResponse({
            'success': True,
            'replies': replies_html,
            'count': replies.count()
        })
    except Exception as e:
        logger.error(f"获取评论回复失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': '获取回复失败，请稍后再试'
        }, status=500)
# 用户互动摘要API
@login_required
def interaction_detail(request, interaction_id):
    """获取单个互动详情"""
    try:
        interaction = UserInteraction.objects.select_related(
            'from_user', 'to_user', 'comment', 'comment__anime'
        ).get(id=interaction_id)

        # 构建详情数据
        data = {
            'interaction': {
                'id': interaction.id,
                'type': interaction.interaction_type,
                'timestamp': interaction.timestamp.isoformat(),
                'from_user': {
                    'id': interaction.from_user.id,
                    'username': interaction.from_user.username,
                    'avatar': interaction.from_user.profile.avatar.url if interaction.from_user.profile.avatar else None
                },
                'to_user': {
                    'id': interaction.to_user.id,
                    'username': interaction.to_user.username,
                    'avatar': interaction.to_user.profile.avatar.url if interaction.to_user.profile.avatar else None
                }
            }
        }

        # 添加评论内容信息
        if interaction.comment:
            data['interaction']['comment_content'] = interaction.comment.content
            data['interaction']['anime_title'] = interaction.comment.anime.title
            data['interaction']['anime_url'] = f'/anime/{interaction.comment.anime.slug}/'

        return JsonResponse({'success': True, 'interaction': data['interaction']})

    except UserInteraction.DoesNotExist:
        return JsonResponse({'success': False, 'error': '互动记录不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
@login_required
def user_interaction_summary(request):
    """
    用户互动摘要API：提供用户互动的汇总数据和最近互动
    """
    try:
        user = request.user

        # 获取发出的互动
        sent_interactions = UserInteraction.objects.filter(from_user=user)

        # 获取收到的互动
        received_interactions = UserInteraction.objects.filter(to_user=user)

        # 统计点赞互动
        likes_given = sent_interactions.filter(interaction_type='like').count()
        likes_received = received_interactions.filter(interaction_type='like').count()

        # 统计回复互动
        replies_given = sent_interactions.filter(interaction_type='reply').count()
        replies_received = received_interactions.filter(interaction_type='reply').count()

        # 获取用户影响力
        profile = user.profile
        influence_score = profile.influence_score

        # 获取用户最近的互动
        recent_interactions = UserInteraction.objects.filter(
            Q(from_user=user) | Q(to_user=user)
        ).select_related('from_user', 'to_user', 'comment').order_by('-timestamp')[:10]

        # 处理互动数据，添加必要信息
        interactions_data = []
        for interaction in recent_interactions:
            interaction_data = {
                'id': interaction.id,
                'type': interaction.interaction_type,
                'timestamp': interaction.timestamp.isoformat(),
                'from_user': {
                    'id': interaction.from_user.id,
                    'username': interaction.from_user.username,
                    'avatar': interaction.from_user.profile.avatar.url if interaction.from_user.profile.avatar else None
                },
                'to_user': {
                    'id': interaction.to_user.id,
                    'username': interaction.to_user.username,
                    'avatar': interaction.to_user.profile.avatar.url if interaction.to_user.profile.avatar else None
                }
            }

            # 添加评论内容信息
            if interaction.comment:
                interaction_data['comment_content'] = interaction.comment.content
                interaction_data['anime_title'] = interaction.comment.anime.title
                interaction_data['anime_url'] = f'/anime/{interaction.comment.anime.id}/'

            interactions_data.append(interaction_data)

        # 构建响应数据
        summary = {
            'likes_given': likes_given,
            'likes_received': likes_received,
            'replies_given': replies_given,
            'replies_received': replies_received,
            'total_sent': sent_interactions.count(),
            'total_received': received_interactions.count(),
            'influence_score': influence_score
        }

        return JsonResponse({
            'success': True,
            'summary': summary,
            'interactions': interactions_data
        })
    except Exception as e:
        logger.error(f"用户互动摘要API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取互动摘要数据失败: {str(e)}'
        }, status=500)


# 获取最近互动API
@login_required
def recent_interactions(request):
    """
    获取最近互动API：提供系统中最近的用户互动数据
    """
    try:
        # 获取最近的50条互动记录
        interactions = UserInteraction.objects.select_related(
            'from_user', 'to_user', 'comment', 'comment__anime'
        ).order_by('-timestamp')[:50]

        # 处理互动数据
        interactions_data = []
        for interaction in interactions:
            # 基本互动信息
            interaction_data = {
                'id': interaction.id,
                'type': interaction.interaction_type,
                'timestamp': interaction.timestamp.isoformat(),
                'from_user': {
                    'id': interaction.from_user.id,
                    'username': interaction.from_user.username,
                    'avatar': interaction.from_user.profile.avatar.url if interaction.from_user.profile.avatar else None
                },
                'to_user': {
                    'id': interaction.to_user.id,
                    'username': interaction.to_user.username,
                    'avatar': interaction.to_user.profile.avatar.url if interaction.to_user.profile.avatar else None
                }
            }

            # 添加评论和动漫信息
            if interaction.comment:
                interaction_data['comment_content'] = interaction.comment.content[:100] + '...' if len(
                    interaction.comment.content) > 100 else interaction.comment.content

                if interaction.comment.anime:
                    interaction_data['anime_title'] = interaction.comment.anime.title
                    interaction_data['anime_url'] = f'/anime/{interaction.comment.anime.id}/'

            interactions_data.append(interaction_data)

        return JsonResponse({
            'success': True,
            'interactions': interactions_data
        })
    except Exception as e:
        logger.error(f"获取最近互动API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取最近互动数据失败: {str(e)}'
        }, status=500)


# 获取最活跃互动用户API
@login_required
def top_interactive_users(request):
    """
    获取最活跃互动用户API：提供系统中最活跃的用户数据
    """
    try:
        # 获取拥有最多互动(发出+接收)的用户
        top_users_data = {}

        # 统计发出的互动
        sent_interactions = UserInteraction.objects.values('from_user').annotate(
            sent_count=Count('id')
        ).order_by('-sent_count')[:20]

        for item in sent_interactions:
            user_id = item['from_user']
            if user_id not in top_users_data:
                top_users_data[user_id] = {'sent': 0, 'received': 0}
            top_users_data[user_id]['sent'] = item['sent_count']

        # 统计收到的互动
        received_interactions = UserInteraction.objects.values('to_user').annotate(
            received_count=Count('id')
        ).order_by('-received_count')[:20]

        for item in received_interactions:
            user_id = item['to_user']
            if user_id not in top_users_data:
                top_users_data[user_id] = {'sent': 0, 'received': 0}
            top_users_data[user_id]['received'] = item['received_count']

        # 计算总互动数并排序
        user_ids = []
        for user_id, counts in top_users_data.items():
            total = counts['sent'] + counts['received']
            user_ids.append((user_id, total))

        # 取前20名
        top_user_ids = [uid for uid, _ in sorted(user_ids, key=lambda x: x[1], reverse=True)[:20]]

        # 获取用户详细信息
        users_info = []
        user_objects = User.objects.filter(id__in=top_user_ids).select_related('profile')

        for user in user_objects:
            # 获取用户的统计数据
            profile = user.profile

            user_info = {
                'id': user.id,
                'username': user.username,
                'avatar': user.profile.avatar.url if user.profile.avatar else None,
                'influence_score': profile.influence_score,
                'social_activity_score': profile.social_activity_score,
                'comment_count': profile.comment_count,
                'replies_count': profile.replies_count,
                'likes_received_count': profile.likes_received_count,
                'likes_given_count': profile.likes_given_count
            }

            users_info.append(user_info)

        # 根据影响力和活跃度重新排序
        users_info.sort(key=lambda x: (x['influence_score'] + x['social_activity_score']), reverse=True)

        return JsonResponse({
            'success': True,
            'users': users_info
        })
    except Exception as e:
        logger.error(f"获取最活跃互动用户API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取活跃用户数据失败: {str(e)}'
        }, status=500)