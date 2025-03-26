# recommendation/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
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

from anime.models import Anime
from .models import RecommendationCache, UserRating, UserComment
from .engine.recommendation_engine import recommendation_engine

# 配置日志记录器
logger = logging.getLogger('django')


# 在views.py中修改get_recommendations函数

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
                        'strategies': [
                            {'code': 'hybrid', 'name': '混合推荐', 'icon': 'fa-magic',
                             'desc': '结合多种算法的综合推荐'},
                            {'code': 'cf', 'name': '协同过滤', 'icon': 'fa-users', 'desc': '基于相似用户喜好的推荐'},
                            {'code': 'content', 'name': '基于内容', 'icon': 'fa-tags',
                             'desc': '根据动漫特征相似度推荐'},
                            {'code': 'ml', 'name': '基于GBDT', 'icon': 'fa-brain',
                             'desc': '使用梯度提升决策树算法的推荐'},
                            {'code': 'popular', 'name': '热门推荐', 'icon': 'fa-fire', 'desc': '当前最热门的动漫'}
                        ]
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
                'strategies': [
                    {'code': 'hybrid', 'name': '混合推荐', 'icon': 'fa-magic', 'desc': '结合多种算法的综合推荐'},
                    {'code': 'cf', 'name': '协同过滤', 'icon': 'fa-users', 'desc': '基于相似用户喜好的推荐'},
                    {'code': 'content', 'name': '基于内容', 'icon': 'fa-tags', 'desc': '根据动漫特征相似度推荐'},
                    {'code': 'ml', 'name': '基于GBDT', 'icon': 'fa-brain', 'desc': '使用梯度提升决策树算法的推荐'},
                    {'code': 'popular', 'name': '热门推荐', 'icon': 'fa-fire', 'desc': '当前最热门的动漫'}
                ]
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
                    'strategies': [
                        {'code': 'hybrid', 'name': '混合推荐', 'icon': 'fa-magic', 'desc': '结合多种算法的综合推荐'},
                        {'code': 'cf', 'name': '协同过滤', 'icon': 'fa-users', 'desc': '基于相似用户喜好的推荐'},
                        {'code': 'content', 'name': '基于内容', 'icon': 'fa-tags', 'desc': '根据动漫特征相似度推荐'},
                        {'code': 'ml', 'name': '基于GBDT', 'icon': 'fa-brain', 'desc': '使用梯度提升决策树算法的推荐'},
                        {'code': 'popular', 'name': '热门推荐', 'icon': 'fa-fire', 'desc': '当前最热门的动漫'}
                    ]
                }
                return render(request, 'recommendation/recommendations.html', context)
            else:
                # 如果没有任何动漫数据，显示错误页面
                raise Exception("数据库中没有动漫数据")

    except Exception as e:
        # 最外层异常处理：显示错误页面
        logger.error(f"致命错误: {str(e)}\n{traceback.format_exc()}")
        context = {
            'error_message': f'获取推荐时发生严重错误，请联系管理员。详情：{str(e)}'
        }
        return render(request, 'recommendation/recommendation_error.html', context)

# API端点
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
                model_path = os.path.join('recommendation', 'engine', 'models', 'bgdt_model.joblib')
                encoders_path = os.path.join('recommendation', 'engine', 'models', 'bgdt_encoders.pkl')

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
def user_activity_dashboard(request):
    """
    用户活动仪表板
    展示用户的评分、评论和推荐历史
    """
    # 获取用户评分数据
    user_ratings = UserRating.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:10]

    # 获取用户评论数据
    user_comments = UserComment.objects.filter(user=request.user).select_related('anime').order_by('-timestamp')[:10]

    # 获取用户的推荐
    try:
        recommendations = recommendation_engine.get_recommendations_for_user(request.user.id, limit=8)
        anime_ids = [rec[0] for rec in recommendations]
        recommended_animes = list(Anime.objects.filter(id__in=anime_ids))

        # 按推荐顺序排序
        id_to_anime = {anime.id: anime for anime in recommended_animes}
        sorted_recommendations = []
        for anime_id, score in recommendations:
            if anime_id in id_to_anime:
                anime = id_to_anime[anime_id]
                # 添加推荐置信度
                anime.confidence = round(score * 100)
                sorted_recommendations.append(anime)
    except Exception as e:
        logger.error(f"获取仪表板推荐时出错: {str(e)}")
        sorted_recommendations = []

    # 获取所有推荐策略
    strategies = [
        {'code': 'hybrid', 'name': '混合推荐', 'icon': 'fa-magic'},
        {'code': 'cf', 'name': '协同过滤', 'icon': 'fa-users'},
        {'code': 'content', 'name': '基于内容', 'icon': 'fa-tags'},
        {'code': 'ml', 'name': '基于GBDT', 'icon': 'fa-brain'},
        {'code': 'popular', 'name': '热门推荐', 'icon': 'fa-fire'}
    ]

    context = {
        'ratings': user_ratings,
        'comments': user_comments,
        'recommendations': sorted_recommendations,
        'strategies': strategies
    }

    return render(request, 'recommendation/user_dashboard.html', context)