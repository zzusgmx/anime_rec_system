# recommendation/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import logging
import os
import traceback
import json

from anime.models import Anime
from .models import RecommendationCache, UserRating, UserComment, UserLike, UserFavorite
from users.models import UserBrowsing
from .engine.recommendation_engine import recommendation_engine

# 配置日志记录器
logger = logging.getLogger('django')

# ========================= 页面视图函数 =========================

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
        paginator = Paginator(favorites_list, 12)  # 每页12个项目
        page = request.GET.get('page', 1)

        try:
            favorites = paginator.page(page)
        except:
            favorites = paginator.page(1)

        context = {
            'favorites': favorites,
            'is_paginated': paginator.num_pages > 1,
            'page_obj': favorites,
            'active_tab': 'favorites'  # 添加active_tab
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


@login_required
def user_activity_dashboard(request):
    """
    用户活动仪表板
    展示用户的评分、评论和推荐历史
    """
    try:
        # 获取用户评分数据
        user_ratings = UserRating.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:10]

        # 获取用户评论数据 - 修改为仅获取5条记录
        user_comments = UserComment.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:3]

        # 转换为JSON格式，用于前端渲染
        ratings_data = []
        for rating in user_ratings:
            ratings_data.append({
                'animeId': rating.anime.id,
                'animeTitle': rating.anime.title,
                'animeSlug': rating.anime.slug,  # 添加slug字段
                'rating': float(rating.rating),
                'date': rating.timestamp.strftime('%Y-%m-%d')
            })

        comments_data = []
        for comment in user_comments:
            comments_data.append({
                'animeId': comment.anime.id,
                'animeTitle': comment.anime.title,
                'animeSlug': comment.anime.slug,  # 添加slug以便构建正确的URL
                'content': comment.content,
                'date': comment.timestamp.strftime('%Y-%m-%d %H:%M'),
                'like_count': comment.like_count,
                'commentId': comment.id  # 添加评论ID用于定位到特定评论
            })

        # 获取默认推荐
        try:
            initial_recommendations = recommendation_engine.get_recommendations_for_user(request.user.id, limit=4)
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
            'recommendations': sorted_recommendations,
            'strategies': get_strategy_list(),
            'active_tab': 'dashboard'  # 添加active_tab
        }

        return render(request, 'recommendation/user_dashboard.html', context)
    except Exception as e:
        logger.error(f"仪表板加载失败: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "加载仪表板数据时出错，请稍后再试")
        return redirect('anime:anime_list')


# ========================= API 视图函数 =========================

# REST API 视图
class RecommendationAPIView(APIView):
    """
    推荐API端点
    提供JSON格式的推荐结果，方便前端异步调用
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 获取请求参数
        strategy = request.query_params.get('strategy', 'hybrid')
        limit = int(request.query_params.get('limit', 10))

        # 验证参数
        if strategy not in ['hybrid', 'cf', 'content', 'popular', 'ml']:
            strategy = 'hybrid'

        if limit > 50:
            limit = 50  # 限制最大结果数

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
                user_id, limit=limit, strategy=strategy
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

            return Response({
                'success': True,
                'strategy': strategy,
                'recommendations': result,
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

        # 更新用户评论计数
        request.user.profile.comment_count += 1
        request.user.profile.save(update_fields=['comment_count'])

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
@require_http_methods(["POST"])
def toggle_like_comment(request, comment_id):
    """
    点赞/取消点赞评论API
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
        logger.error(f"点赞操作失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '操作失败，请稍后再试'
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

        # 更新用户评分计数（如果是新评分）
        if was_new:
            request.user.profile.rating_count += 1
            request.user.profile.save(update_fields=['rating_count'])

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
        limit = int(request.GET.get('limit', 4))

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
        user_comments = UserComment.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:3]

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