from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.db.models.functions import  TruncDate
import logging
import pandas as pd
from datetime import timedelta
import traceback
import io
import matplotlib
from django.db.models import Count, Avg, Q, Max
matplotlib.use('Agg')  # 服务器端无界面环境
import seaborn as sns
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from anime.models import Anime, AnimeType
from recommendation.models import UserRating, UserComment, UserFavorite, AnimeLike, UserInteraction
from users.models import UserBrowsing, Profile, UserPreference
from .models import VisualizationPreference, CustomDashboard, VisualizationExport
from .services import DataProcessingService, VisualizationService
from django.db.models.functions import TruncMonth

# 配置日志
logger = logging.getLogger('django')
import json
from django.core.serializers.json import DjangoJSONEncoder


@login_required
def visualization_dashboard(request):
    """主可视化仪表盘页面"""
    try:
        # 获取用户的默认仪表盘或创建一个
        dashboard = CustomDashboard.objects.filter(
            user=request.user, is_default=True
        ).first()

        if not dashboard:
            # 创建默认仪表盘
            dashboard = CustomDashboard.objects.create(
                user=request.user,
                name="我的仪表盘",
                is_default=True,
                layout={
                    'widgets': [
                        {'id': 'rating_distribution', 'title': '评分分布', 'type': 'chart',
                         'position': {'row': 0, 'col': 0, 'width': 6, 'height': 4}},
                        {'id': 'viewing_trends', 'title': '观看趋势', 'type': 'chart',
                         'position': {'row': 0, 'col': 6, 'width': 6, 'height': 4}},
                        {'id': 'genre_preference', 'title': '类型偏好', 'type': 'chart',
                         'position': {'row': 4, 'col': 0, 'width': 6, 'height': 4}},
                        {'id': 'activity_summary', 'title': '活动摘要', 'type': 'stats',
                         'position': {'row': 4, 'col': 6, 'width': 6, 'height': 4}}
                    ]
                }
            )

        # 获取用户的其他仪表盘
        other_dashboards = CustomDashboard.objects.filter(
            user=request.user, is_default=False
        ).order_by('name')

        # 获取或创建用户的可视化偏好
        pref, created = VisualizationPreference.objects.get_or_create(user=request.user)

        # 确保布局是有效的JSON字符串
        dashboard_layout_json = json.dumps(dashboard.layout, cls=DjangoJSONEncoder)

        context = {
            'dashboard': dashboard,
            'other_dashboards': other_dashboards,
            'preferences': pref,
            'active_tab': 'dashboard',
            'page_title': '数据可视化仪表盘',
            'dashboard_layout_json': dashboard_layout_json
        }

        return render(request, 'visualizations/dashboard.html', context)
    except Exception as e:
        logger.error(f"可视化仪表盘加载失败: {str(e)}\n{traceback.format_exc()}")
        return render(request, 'visualizations/visualization_error.html', {
            'error_message': '加载可视化仪表盘失败，请稍后再试。',
            'error_details': str(e) if settings.DEBUG else None
        })

@login_required
def user_insights(request):
    """用户数据洞察页面"""
    try:
        # 获取用户基本统计数据
        user_stats = {
            'rating_count': UserRating.objects.filter(user=request.user).count(),
            'comment_count': UserComment.objects.filter(user=request.user).count(),
            'favorite_count': UserFavorite.objects.filter(user=request.user).count(),
            'like_count': AnimeLike.objects.filter(user=request.user).count(),
            'browsing_count': UserBrowsing.objects.filter(user=request.user).count(),
        }

        # 获取动漫类型偏好
        genre_preferences = DataProcessingService.get_user_genre_preferences(request.user)

        # 获取评分趋势数据
        rating_trends = DataProcessingService.get_user_rating_trends(request.user)

        context = {
            'user_stats': user_stats,
            'genre_preferences': genre_preferences,
            'rating_trends': rating_trends,
            'active_tab': 'insights',
            'page_title': '个人数据洞察'
        }

        return render(request, 'visualizations/user_insights.html', context)
    except Exception as e:
        logger.error(f"用户洞察页面加载失败: {str(e)}\n{traceback.format_exc()}")
        return render(request, 'visualizations/visualization_error.html', {
            'error_message': '加载用户洞察失败，请稍后再试。',
            'error_details': str(e) if settings.DEBUG else None
        })

@login_required
def comparison_tool(request):
    """比较工具页面"""
    try:
        # 获取所有动漫类型
        anime_types = AnimeType.objects.all().order_by('name')

        # 获取用户评分的动漫
        rated_anime = Anime.objects.filter(
            userrating__user=request.user
        ).distinct().order_by('-userrating__rating')[:10]

        context = {
            'anime_types': anime_types,
            'rated_anime': rated_anime,
            'active_tab': 'comparison',
            'page_title': '比较工具'
        }

        return render(request, 'visualizations/comparison_tool.html', context)
    except Exception as e:
        logger.error(f"比较工具页面加载失败: {str(e)}\n{traceback.format_exc()}")
        return render(request, 'visualizations/visualization_error.html', {
            'error_message': '加载比较工具失败，请稍后再试。',
            'error_details': str(e) if settings.DEBUG else None
        })


@login_required
@require_POST
def save_dashboard(request):
    """保存仪表盘布局"""
    try:
        data = json.loads(request.body)
        dashboard_id = data.get('dashboard_id')
        layout = data.get('layout')
        name = data.get('name', 'My Dashboard')

        if dashboard_id:
            # 更新现有仪表盘
            dashboard = get_object_or_404(CustomDashboard, id=dashboard_id, user=request.user)
            dashboard.name = name
            dashboard.layout = layout
            dashboard.save()
        else:
            # 创建新仪表盘
            dashboard = CustomDashboard.objects.create(
                user=request.user,
                name=name,
                layout=layout
            )

        return JsonResponse({
            'success': True,
            'dashboard_id': dashboard.id,
            'message': '仪表盘已保存'
        })
    except Exception as e:
        logger.error(f"保存仪表盘失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def set_default_dashboard(request, dashboard_id):
    """设置默认仪表盘"""
    try:
        # 首先取消所有默认设置
        CustomDashboard.objects.filter(user=request.user, is_default=True).update(is_default=False)

        # 设置新的默认仪表盘
        dashboard = get_object_or_404(CustomDashboard, id=dashboard_id, user=request.user)
        dashboard.is_default = True
        dashboard.save()

        return JsonResponse({
            'success': True,
            'message': f'已将"{dashboard.name}"设为默认仪表盘'
        })
    except Exception as e:
        logger.error(f"设置默认仪表盘失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def delete_dashboard(request, dashboard_id):
    """删除仪表盘"""
    try:
        dashboard = get_object_or_404(CustomDashboard, id=dashboard_id, user=request.user)

        # 不允许删除默认仪表盘
        if dashboard.is_default:
            return JsonResponse({
                'success': False,
                'error': '不能删除默认仪表盘'
            }, status=400)

        dashboard_name = dashboard.name
        dashboard.delete()

        return JsonResponse({
            'success': True,
            'message': f'已删除仪表盘"{dashboard_name}"'
        })
    except Exception as e:
        logger.error(f"删除仪表盘失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def update_visualization_preferences(request):
    """更新可视化偏好设置"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        default_view = data.get('default_view')
        chart_types = data.get('chart_types', {})

        pref, created = VisualizationPreference.objects.get_or_create(user=request.user)

        if theme:
            pref.theme = theme

        if default_view:
            pref.default_view = default_view

        if chart_types:
            pref.chart_types = chart_types

        pref.save()

        return JsonResponse({
            'success': True,
            'message': '偏好设置已更新'
        })
    except Exception as e:
        logger.error(f"更新可视化偏好失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_GET
def export_visualization(request, chart_type):
    """导出可视化图表"""
    try:
        format = request.GET.get('format', 'png')
        title = request.GET.get('title', f'{chart_type}_export')

        # 获取图表数据
        if chart_type == 'rating_distribution':
            data = VisualizationService.generate_rating_distribution(request.user)
        elif chart_type == 'genre_preference':
            data = VisualizationService.generate_genre_preference(request.user)
        elif chart_type == 'viewing_trends':
            data = VisualizationService.generate_viewing_trends(request.user)
        elif chart_type == 'activity_summary':
            data = VisualizationService.generate_activity_summary(request.user)
        else:
            return JsonResponse({
                'success': False,
                'error': f'不支持的图表类型: {chart_type}'
            }, status=400)

        # 创建图表
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)

        if chart_type == 'rating_distribution':
            # 绘制评分分布图
            sns.barplot(x='rating', y='count', data=pd.DataFrame(data), ax=ax)
            ax.set_title('评分分布')
            ax.set_xlabel('评分')
            ax.set_ylabel('计数')
        elif chart_type == 'genre_preference':
            # 绘制类型偏好图
            df = pd.DataFrame(data)
            sns.barplot(x='value', y='name', data=df.sort_values('value', ascending=False), ax=ax)
            ax.set_title('类型偏好')
            ax.set_xlabel('偏好分数')
            ax.set_ylabel('动漫类型')
        elif chart_type == 'viewing_trends':
            # 绘制观看趋势图
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            ax.plot(df['date'], df['views'], marker='o', linestyle='-', label='浏览量')
            ax.plot(df['date'], df['ratings'], marker='s', linestyle='--', label='评分数')
            ax.set_title('观看趋势')
            ax.set_xlabel('日期')
            ax.set_ylabel('计数')
            ax.legend()
        elif chart_type == 'activity_summary':
            # 绘制活动摘要图
            labels = ['浏览', '评分', '评论', '收藏']
            values = [data[0]['value'], data[1]['value'], data[2]['value'], data[3]['value']]
            colors = [data[0]['color'], data[1]['color'], data[2]['color'], data[3]['color']]
            ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors)
            ax.set_title('活动摘要')

        # 导出图表
        if format == 'png':
            # 导出PNG图片
            canvas = FigureCanvas(fig)
            output = io.BytesIO()
            canvas.print_png(output)

            # 创建导出记录
            export = VisualizationExport.objects.create(
                user=request.user,
                title=title,
                format=format,
                file_path=f'visualizations/exports/{request.user.id}_{chart_type}_{timezone.now().strftime("%Y%m%d%H%M%S")}.png'
            )

            response = HttpResponse(output.getvalue(), content_type='image/png')
            response['Content-Disposition'] = f'attachment; filename="{title}.png"'
            return response
        elif format == 'svg':
            # 导出SVG图片
            output = io.BytesIO()
            fig.savefig(output, format='svg')

            # 创建导出记录
            export = VisualizationExport.objects.create(
                user=request.user,
                title=title,
                format=format,
                file_path=f'visualizations/exports/{request.user.id}_{chart_type}_{timezone.now().strftime("%Y%m%d%H%M%S")}.svg'
            )

            response = HttpResponse(output.getvalue(), content_type='image/svg+xml')
            response['Content-Disposition'] = f'attachment; filename="{title}.svg"'
            return response
        elif format == 'json':
            # 导出JSON数据
            export = VisualizationExport.objects.create(
                user=request.user,
                title=title,
                format=format,
                file_path=f'visualizations/exports/{request.user.id}_{chart_type}_{timezone.now().strftime("%Y%m%d%H%M%S")}.json'
            )

            response = JsonResponse(data, safe=False)
            response['Content-Disposition'] = f'attachment; filename="{title}.json"'
            return response
        else:
            return JsonResponse({
                'success': False,
                'error': f'不支持的导出格式: {format}'
            }, status=400)
    except Exception as e:
        logger.error(f"导出可视化失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# 在recommendation/views.py中添加的可视化数据API

@login_required
def visualization_rating_distribution(request):
    """
    评分分布数据API - 为可视化提供用户评分分布数据
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
def visualization_genre_preference(request):
    """
    类型偏好分析API - 为可视化提供用户动漫类型偏好数据
    """
    try:
        user = request.user

        # 获取用户评分过的动漫的类型
        rated_anime_types = UserRating.objects.filter(user=user).select_related('anime__type')
        type_data = {}

        # 统计每个类型的评分情况
        for rating in rated_anime_types:
            if not rating.anime.type:
                continue

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
            if not browsing.anime.type:
                continue

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
            if not favorite.anime.type:
                continue

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
def visualization_viewing_trends(request):
    """
    观看趋势分析API - 为可视化提供用户近期活跃度趋势数据
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


@login_required
def visualization_activity_summary(request):
    """
    活动摘要数据API - 为可视化提供用户各类活动的统计数据
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
        logger.error(f"活动摘要数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取活动摘要数据失败: {str(e)}'
        }, status=500)


@login_required
def visualization_journey_timeline(request):
    """
    用户旅程时间线API - 为可视化提供用户使用系统的完整旅程数据
    """
    try:
        user = request.user

        # 获取一段时间内用户的所有活动
        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)  # 获取90天内的活动

        # 获取浏览记录
        browsing_events = UserBrowsing.objects.filter(
            user=user,
            last_browsed__gte=start_date,
            last_browsed__lte=end_date
        ).values('anime__title', 'last_browsed').order_by('last_browsed')

        # 获取评分记录
        rating_events = UserRating.objects.filter(
            user=user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('anime__title', 'rating', 'timestamp').order_by('timestamp')

        # 获取评论记录
        comment_events = UserComment.objects.filter(
            user=user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('anime__title', 'content', 'timestamp').order_by('timestamp')

        # 获取收藏记录
        favorite_events = UserFavorite.objects.filter(
            user=user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('anime__title', 'timestamp').order_by('timestamp')

        # 获取点赞记录
        like_events = AnimeLike.objects.filter(
            user=user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('anime__title', 'timestamp').order_by('timestamp')

        # 将所有事件合并到一个列表中
        events = []

        # 浏览事件
        for event in browsing_events:
            events.append({
                'type': 'browse',
                'title': event['anime__title'],
                'date': event['last_browsed'].isoformat(),
                'detail': '浏览了这部动漫'
            })

        # 评分事件
        for event in rating_events:
            events.append({
                'type': 'rate',
                'title': event['anime__title'],
                'date': event['timestamp'].isoformat(),
                'detail': f'评分: {event["rating"]}'
            })

        # 评论事件
        for event in comment_events:
            events.append({
                'type': 'comment',
                'title': event['anime__title'],
                'date': event['timestamp'].isoformat(),
                'detail': f'评论: {event["content"][:50]}...' if len(
                    event['content']) > 50 else f'评论: {event["content"]}'
            })

        # 收藏事件
        for event in favorite_events:
            events.append({
                'type': 'favorite',
                'title': event['anime__title'],
                'date': event['timestamp'].isoformat(),
                'detail': '收藏了这部动漫'
            })

        # 点赞事件
        for event in like_events:
            events.append({
                'type': 'like',
                'title': event['anime__title'],
                'date': event['timestamp'].isoformat(),
                'detail': '点赞了这部动漫'
            })

        # 按时间排序
        events = sorted(events, key=lambda x: x['date'])

        return JsonResponse({
            'success': True,
            'data': events
        })
    except Exception as e:
        logger.error(f"用户旅程时间线API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取用户旅程时间线数据失败: {str(e)}'
        }, status=500)


@login_required
def visualization_network_data(request):
    """
    用户交互网络数据API - 为可视化提供用户交互网络图数据
    """
    try:
        user = request.user
        user_focused = request.GET.get('user_focused', 'true') == 'true'

        # 定义节点数量限制
        max_nodes = 50

        if user_focused:
            # 获取与当前用户相关的交互
            interactions = UserInteraction.objects.filter(
                Q(from_user=user) | Q(to_user=user)
            ).select_related('from_user', 'to_user').order_by('-timestamp')[:200]

            # 收集节点
            user_ids = set([user.id])
            for interaction in interactions:
                user_ids.add(interaction.from_user.id)
                user_ids.add(interaction.to_user.id)
                if len(user_ids) >= max_nodes:
                    break

            # 限制总节点数
            user_ids = list(user_ids)[:max_nodes]

            # 过滤关联的交互
            filtered_interactions = [i for i in interactions
                                     if i.from_user.id in user_ids and i.to_user.id in user_ids]
        else:
            # 全局交互网络
            # 获取所有交互
            interactions = UserInteraction.objects.all().select_related(
                'from_user', 'to_user'
            ).order_by('-timestamp')[:500]

            # 计算每个用户的交互总数
            user_interaction_count = {}
            for interaction in interactions:
                user_interaction_count[interaction.from_user.id] = user_interaction_count.get(interaction.from_user.id,
                                                                                              0) + 1
                user_interaction_count[interaction.to_user.id] = user_interaction_count.get(interaction.to_user.id,
                                                                                            0) + 1

            # 选择交互最多的用户
            sorted_users = sorted(user_interaction_count.items(), key=lambda x: x[1], reverse=True)
            top_users = [user_id for user_id, _ in sorted_users[:max_nodes]]

            # 过滤关联的交互
            filtered_interactions = [i for i in interactions
                                     if i.from_user.id in top_users and i.to_user.id in top_users]

        # 构建节点数据
        nodes = []
        user_profiles = {}

        # 获取用户资料数据
        for user_id in sorted(list(set([i.from_user.id for i in filtered_interactions] +
                                       [i.to_user.id for i in filtered_interactions]))):
            try:
                profile = Profile.objects.get(user_id=user_id)
                user_profiles[user_id] = profile

                nodes.append({
                    'id': str(user_id),  # D3.js需要字符串ID
                    'username': profile.user.username,
                    'influence': profile.influence_score or 0,
                    'activity': profile.social_activity_score or 0,
                    'size': 10 + ((profile.influence_score or 0) + (profile.social_activity_score or 0)) / 10
                })
            except Profile.DoesNotExist:
                # 如果用户没有资料，创建一个基本节点
                try:
                    username = User.objects.get(id=user_id).username
                except User.DoesNotExist:
                    username = f"User {user_id}"

                nodes.append({
                    'id': str(user_id),
                    'username': username,
                    'influence': 0,
                    'activity': 0,
                    'size': 10
                })

        # 构建连接数据
        links = []
        for interaction in filtered_interactions:
            links.append({
                'source': str(interaction.from_user.id),
                'target': str(interaction.to_user.id),
                'type': interaction.interaction_type,
                'strength': interaction.strength or 1,
                'width': (interaction.strength or 1) * 2  # 线宽基于交互强度
            })

        return JsonResponse({
            'success': True,
            'data': {
                'nodes': nodes,
                'links': links
            }
        })
    except Exception as e:
        logger.error(f"用户交互网络数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取用户交互网络数据失败: {str(e)}'
        }, status=500)


@login_required
def visualization_recommendation_insights(request):
    """
    推荐洞察数据API - 为可视化提供推荐系统洞察数据
    """
    try:
        user = request.user

        # 获取用户的评分记录
        user_ratings = UserRating.objects.filter(user=user).select_related('anime')

        # 如果用户没有任何评分，返回基本数据
        if not user_ratings.exists():
            return JsonResponse({
                'success': True,
                'data': {
                    'avgUserRating': 0,
                    'topGenres': [],
                    'ratingDistribution': [],
                    'recommendationFactors': []
                },
                'message': '用户没有足够的评分数据来生成洞察'
            })

        # 计算用户平均评分
        avg_rating = user_ratings.aggregate(avg=Avg('rating'))['avg'] or 0

        # 获取用户评分最高的类型
        genre_ratings = {}
        for rating in user_ratings:
            if rating.anime.type:
                genre = rating.anime.type.name
                if genre not in genre_ratings:
                    genre_ratings[genre] = {
                        'count': 0,
                        'total': 0
                    }
                genre_ratings[genre]['count'] += 1
                genre_ratings[genre]['total'] += rating.rating

        # 计算每个类型的平均评分
        top_genres = []
        for genre, data in genre_ratings.items():
            avg = data['total'] / data['count']
            top_genres.append({
                'name': genre,
                'averageRating': round(avg, 1),
                'count': data['count']
            })

        # 按平均评分排序
        top_genres.sort(key=lambda x: x['averageRating'], reverse=True)
        top_genres = top_genres[:5]  # 取前5个

        # 获取评分分布
        rating_distribution = {}
        for r in range(1, 6):  # 1-5分
            count = user_ratings.filter(rating__gte=r - 0.25, rating__lt=r + 0.75).count()
            rating_distribution[r] = count

        # 转换为列表格式
        rating_dist_list = [
            {'rating': r, 'count': rating_distribution[r]}
            for r in range(1, 6)
        ]

        # 计算推荐因素 - 这里使用模拟数据，实际项目中可以从推荐引擎获取
        recommendation_factors = [
            {'name': '用户评分', 'weight': 0.35, 'description': '基于您过去的评分记录'},
            {'name': '内容相似度', 'weight': 0.25, 'description': '基于动漫的类型和特征相似度'},
            {'name': '浏览历史', 'weight': 0.15, 'description': '基于您过去浏览过的动漫'},
            {'name': '收藏记录', 'weight': 0.15, 'description': '基于您收藏的动漫'},
            {'name': '社区趋势', 'weight': 0.10, 'description': '基于社区中的热门动漫'}
        ]

        # 构建完整的洞察数据
        insights = {
            'avgUserRating': round(avg_rating, 1),
            'topGenres': top_genres,
            'ratingDistribution': rating_dist_list,
            'recommendationFactors': recommendation_factors
        }

        return JsonResponse({
            'success': True,
            'data': insights
        })
    except Exception as e:
        logger.error(f"推荐洞察数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取推荐洞察数据失败: {str(e)}'
        }, status=500)

@login_required
def visualization_community_activity(request):
    """
    社区活动趋势数据API - 提供社区各类活动的趋势数据
    """
    try:
        # 获取过去30天的数据
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)
        date_range = [start_date + timedelta(days=i) for i in range(30)]

        # 查询每日评论数据
        comment_data = (
            UserComment.objects
            .filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # 查询每日评分数据
        rating_data = (
            UserRating.objects
            .filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # 查询每日收藏数据
        favorite_data = (
            UserFavorite.objects
            .filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # 将查询结果转换为字典，以日期为键
        comment_dict = {item['date'].isoformat(): item['count'] for item in comment_data}
        rating_dict = {item['date'].isoformat(): item['count'] for item in rating_data}
        favorite_dict = {item['date'].isoformat(): item['count'] for item in favorite_data}

        # 构建完整的日期序列数据
        result = []
        for date in date_range:
            date_str = date.isoformat()
            result.append({
                'date': date_str,
                'comments': comment_dict.get(date_str, 0),
                'ratings': rating_dict.get(date_str, 0),
                'favorites': favorite_dict.get(date_str, 0),
                'total': comment_dict.get(date_str, 0) + rating_dict.get(date_str, 0) + favorite_dict.get(date_str, 0)
            })

        return JsonResponse({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"社区活动趋势数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取社区活动趋势数据失败: {str(e)}'
        }, status=500)


@login_required
def visualization_user_distribution(request):
    """
    用户分布数据API - 提供用户活跃度和影响力分布数据
    """
    try:
        # 获取所有用户资料
        profiles = Profile.objects.all()

        # 活跃度分布
        activity_ranges = [
            {'range': '非常低 (0-20)', 'min': 0, 'max': 20, 'count': 0},
            {'range': '较低 (21-40)', 'min': 21, 'max': 40, 'count': 0},
            {'range': '中等 (41-60)', 'min': 41, 'max': 60, 'count': 0},
            {'range': '较高 (61-80)', 'min': 61, 'max': 80, 'count': 0},
            {'range': '非常高 (81-100)', 'min': 81, 'max': 100, 'count': 0}
        ]

        # 影响力分布
        influence_ranges = [
            {'range': '非常低 (0-20)', 'min': 0, 'max': 20, 'count': 0},
            {'range': '较低 (21-40)', 'min': 21, 'max': 40, 'count': 0},
            {'range': '中等 (41-60)', 'min': 41, 'max': 60, 'count': 0},
            {'range': '较高 (61-80)', 'min': 61, 'max': 80, 'count': 0},
            {'range': '非常高 (81-100)', 'min': 81, 'max': 100, 'count': 0}
        ]

        # 统计各范围的用户数量
        for profile in profiles:
            # 处理活跃度
            activity_score = profile.social_activity_score or 0
            for range_data in activity_ranges:
                if range_data['min'] <= activity_score <= range_data['max']:
                    range_data['count'] += 1
                    break

            # 处理影响力
            influence_score = profile.influence_score or 0
            for range_data in influence_ranges:
                if range_data['min'] <= influence_score <= range_data['max']:
                    range_data['count'] += 1
                    break

        # 转换为可视化数据格式
        activity_distribution = [{'name': r['range'], 'value': r['count']} for r in activity_ranges]
        influence_distribution = [{'name': r['range'], 'value': r['count']} for r in influence_ranges]

        return JsonResponse({
            'success': True,
            'data': {
                'activityDistribution': activity_distribution,
                'influenceDistribution': influence_distribution
            }
        })
    except Exception as e:
        logger.error(f"用户分布数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取用户分布数据失败: {str(e)}'
        }, status=500)


@login_required
def visualization_discussion_stats(request):
    """
    讨论统计数据API - 提供动漫讨论热度和趋势数据
    """
    try:
        # 获取按类型分组的讨论数据
        discussion_by_genre = (
            UserComment.objects
            .filter(anime__type__isnull=False)
            .values('anime__type__name')
            .annotate(comment_count=Count('id'))
            .order_by('-comment_count')
        )

        # 转换为可视化数据格式
        genre_discussion = []
        for item in discussion_by_genre:
            genre_name = item['anime__type__name']
            if genre_name:  # 确保类型名称不为空
                genre_discussion.append({
                    'name': genre_name,
                    'value': item['comment_count']
                })

        # 获取最近30天的讨论趋势
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)
        date_range = [start_date + timedelta(days=i) for i in range(30)]

        # 查询每日讨论数据
        discussion_trend_data = (
            UserComment.objects
            .filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # 将查询结果转换为字典
        discussion_dict = {item['date'].isoformat(): item['count'] for item in discussion_trend_data}

        # 构建完整的日期序列数据
        discussion_trend = []
        for date in date_range:
            date_str = date.isoformat()
            discussion_trend.append({
                'date': date_str,
                'count': discussion_dict.get(date_str, 0)
            })

        return JsonResponse({
            'success': True,
            'data': {
                'discussionByGenre': genre_discussion[:10],  # 限制为前10个类型
                'discussionTrend': discussion_trend
            }
        })
    except Exception as e:
        logger.error(f"讨论统计数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取讨论统计数据失败: {str(e)}'
        }, status=500)


# 完成之前被截断的函数
@login_required
def visualization_interaction_stats(request):
    """
    互动统计数据API - 提供用户互动类型分布和趋势数据
    """
    try:
        # 获取互动类型分布
        interaction_type_data = (
            UserInteraction.objects
            .values('interaction_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # 转换为可视化数据格式
        interaction_by_type = []
        for item in interaction_type_data:
            interaction_type = item['interaction_type']
            if interaction_type:  # 确保互动类型不为空
                type_name = {
                    'like': '点赞',
                    'reply': '回复',
                    'mention': '提及',
                    'follow': '关注'
                }.get(interaction_type, interaction_type)

                interaction_by_type.append({
                    'name': type_name,
                    'value': item['count']
                })

        # 获取最近30天的互动趋势
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)
        date_range = [start_date + timedelta(days=i) for i in range(30)]

        # 查询每日互动数据
        interaction_trend_data = (
            UserInteraction.objects
            .filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date', 'interaction_type')
            .annotate(count=Count('id'))
            .order_by('date', 'interaction_type')
        )

        # 构建互动趋势数据结构
        # 首先为每个互动类型创建一个数据字典
        trend_dict = {}
        for item in interaction_trend_data:
            date_str = item['date'].isoformat()
            interaction_type = item['interaction_type']

            if interaction_type not in trend_dict:
                trend_dict[interaction_type] = {}

            trend_dict[interaction_type][date_str] = item['count']

        # 构建完整的趋势数据
        interaction_trend = []

        # 为每个互动类型创建一个数据系列
        for interaction_type, dates in trend_dict.items():
            type_name = {
                'like': '点赞',
                'reply': '回复',
                'mention': '提及',
                'follow': '关注'
            }.get(interaction_type, interaction_type)

            series_data = []
            for date in date_range:
                date_str = date.isoformat()
                series_data.append({
                    'x': date_str,
                    'y': dates.get(date_str, 0)
                })

            interaction_trend.append({
                'name': type_name,
                'data': series_data
            })

        return JsonResponse({
            'success': True,
            'data': {
                'interactionByType': interaction_by_type,
                'interactionTrend': interaction_trend
            }
        })
    except Exception as e:
        logger.error(f"互动统计数据API错误: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'获取互动统计数据失败: {str(e)}'
        }, status=500)
@login_required
def community_analysis(request):
    """社区分析页面"""
    try:
        # 社区基本统计数据
        community_stats = {
            'active_users_count': Profile.objects.filter(social_activity_score__gt=0).count(),
            'comment_count': UserComment.objects.count(),
            'interaction_count': UserInteraction.objects.count(),
            'hot_topics_count': Anime.objects.annotate(comments_total=Count('comments')).filter(
                comments_total__gt=0).count()
        }

        # 获取最活跃用户
        active_users = Profile.objects.annotate(
            user_comment_count=Count('user__comments'),
            user_rating_count=Count('user__ratings'),
            user_like_count=Count('user__likes')
        ).order_by('-social_activity_score')[:10]

        # 获取最具影响力用户 - 修复此处字段名称错误
        influential_users = Profile.objects.annotate(
            # 使用interactions_received而不是received_interactions
            follower_count=Count('user__interactions_received',
                               filter=Q(user__interactions_received__interaction_type='follow')),
            helpful_count=Count('user__interactions_received',
                               filter=Q(user__interactions_received__interaction_type='like')),
            mention_count=Count('user__interactions_received',
                               filter=Q(user__interactions_received__interaction_type='mention'))
        ).order_by('-influence_score')[:10]

        # 获取热门讨论的动漫
        hot_discussions_data = Anime.objects.annotate(
            comments_total=Count('comments'),
            latest_comment_date=Max('comments__timestamp')
        ).filter(comments_total__gt=0).order_by('-comments_total')[:10]

        # 计算热门讨论的动漫讨论热度百分比
        hot_discussions = []
        max_comments = hot_discussions_data.first().comments_total if hot_discussions_data.exists() else 1

        for anime in hot_discussions_data:
            # 计算讨论百分比
            discussion_percentage = min(100, round((anime.comments_total / max_comments) * 100))

            # 获取最热门的评论
            top_comment = UserComment.objects.filter(anime=anime).order_by('-like_count', '-timestamp').first()

            # 添加到结果列表
            hot_discussions.append({
                'id': anime.id,
                'title': anime.title,
                'rating_avg': anime.rating_avg,
                'type': anime.type,
                'comment_count': anime.comments_total,
                'latest_comment_date': anime.latest_comment_date,
                'discussion_percentage': discussion_percentage,
                'top_comment': top_comment
            })

        context = {
            'community_stats': community_stats,
            'active_users': active_users,
            'influential_users': influential_users,
            'hot_discussions': hot_discussions,
            'active_tab': 'community',
            'page_title': '社区分析'
        }

        return render(request, 'visualizations/community_analysis.html', context)
    except Exception as e:
        logger.error(f"社区分析页面加载失败: {str(e)}\n{traceback.format_exc()}")
        return render(request, 'visualizations/visualization_error.html', {
            'error_message': '加载社区分析失败，请稍后再试。',
            'error_details': str(e) if settings.DEBUG else None
        })



