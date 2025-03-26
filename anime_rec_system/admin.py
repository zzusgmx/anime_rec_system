# anime_rec_system/admin.py
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from import_export.admin import ImportExportMixin
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count, Avg, Sum, Max
from django.db.models.functions import TruncDay, TruncMonth
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponseForbidden
from functools import wraps

# 自定义Admin站点配置
admin.site.site_header = "动漫推荐系统管理后台"
admin.site.site_title = "动漫推荐系统"
admin.site.index_title = "控制中心"

# 取消注册默认的Group模型
admin.site.unregister(Group)


# 注册全局admin过滤器 - 前一次错误的缺失符号
class ActiveUserFilter(admin.SimpleListFilter):
    """活跃用户过滤器"""
    title = '用户活跃度'
    parameter_name = 'activity'

    def lookups(self, request, model_admin):
        return (
            ('high', '高活跃度'),
            ('medium', '中活跃度'),
            ('low', '低活跃度'),
            ('inactive', '不活跃'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.annotate(
                activity=Count('ratings') + Count('comments') + Count('favorites')
            ).filter(activity__gt=20)
        if self.value() == 'medium':
            return queryset.annotate(
                activity=Count('ratings') + Count('comments') + Count('favorites')
            ).filter(activity__gt=5, activity__lte=20)
        if self.value() == 'low':
            return queryset.annotate(
                activity=Count('ratings') + Count('comments') + Count('favorites')
            ).filter(activity__gt=0, activity__lte=5)
        if self.value() == 'inactive':
            return queryset.annotate(
                activity=Count('ratings') + Count('comments') + Count('favorites')
            ).filter(activity=0)


# 自定义装饰器 - 用于视图函数的权限控制
def moderator_required(view_func):
    """检查用户是否为管理员或内容审核员的装饰器"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 检查用户权限
        if request.user.is_staff or request.user.groups.filter(name='Moderators').exists():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("您没有权限执行此操作")

    return _wrapped_view


def owner_required(model_class):
    """检查用户是否为资源所有者的装饰器"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 获取对象ID
            obj_id = kwargs.get('pk') or kwargs.get('id')

            if not obj_id:
                return HttpResponseForbidden("无法验证资源所有权")

            try:
                # 查询对象
                obj = model_class.objects.get(pk=obj_id)

                # 检查所有权
                if hasattr(obj, 'user') and obj.user == request.user:
                    return view_func(request, *args, **kwargs)
                elif hasattr(obj, 'user_id') and obj.user_id == request.user.id:
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("您不是该资源的所有者")
            except model_class.DoesNotExist:
                return HttpResponseForbidden("资源不存在")

        return _wrapped_view

    return decorator


class BaseModelAdmin(ImportExportMixin, admin.ModelAdmin):
    """
    自定义Admin基类，所有模型Admin可继承此类获取通用功能

    特性:
    - 导入/导出功能
    - 通用样式增强
    - 预设列表和表单配置
    """
    # 默认显示创建和更新时间
    list_display = ('__str__', 'created_at', 'updated_at')

    # 默认按创建时间倒序排序
    ordering = ('-created_at',)

    # 默认时间范围过滤器
    date_hierarchy = 'created_at'

    # 默认允许的操作
    actions_on_top = True
    actions_on_bottom = True

    # 显示搜索帮助文本
    search_help_text = "输入关键词进行搜索..."

    # 导入/导出配置
    import_export_change_list_template = 'admin/import_export/change_list.html'

    # 保存当前用户
    def save_model(self, request, obj, form, change):
        """保存模型时自动记录操作用户"""
        if hasattr(obj, 'created_by') and not obj.pk:
            obj.created_by = request.user
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def colored_status(self, obj):
        """状态字段彩色显示"""
        if not hasattr(obj, 'status'):
            return '-'

        colors = {
            'active': 'green',
            'pending': 'orange',
            'inactive': 'red',
            'published': 'green',
            'draft': 'gray',
        }

        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )

    colored_status.short_description = '状态'


class DashboardAdmin(admin.AdminSite):
    """自定义Admin站点，添加仪表板和数据可视化功能"""

    def get_urls(self):
        """添加自定义URL"""
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
            path('rating-analytics/', self.admin_view(self.rating_analytics_view), name='rating-analytics'),
            path('favorite-analytics/', self.admin_view(self.favorite_analytics_view), name='favorite-analytics'),
            path('api/chart-data/', self.admin_view(self.chart_data_view), name='chart_data'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """仪表板视图，显示系统概览"""
        # 获取基础统计数据
        from anime.models import Anime, AnimeType
        from django.contrib.auth.models import User
        from recommendation.models import UserRating, UserComment, UserFavorite

        # 系统概览数据
        context = {
            'title': '系统仪表板',
            'anime_count': Anime.objects.count(),
            'anime_type_count': AnimeType.objects.count(),
            'user_count': User.objects.count(),
            'rating_count': UserRating.objects.count(),
            'comment_count': UserComment.objects.count(),
            'favorite_count': UserFavorite.objects.count(),
        }

        # 获取最新用户
        context['latest_users'] = User.objects.order_by('-date_joined')[:5]

        # 获取最受欢迎的动漫
        context['popular_anime'] = Anime.objects.order_by('-popularity')[:5]

        # 获取评分最高的动漫
        context['top_rated_anime'] = Anime.objects.order_by('-rating_avg')[:5]

        # 最近的评论
        context['recent_comments'] = UserComment.objects.select_related('user', 'anime').order_by('-created_at')[:5]

        # 活跃用户
        active_users = User.objects.annotate(
            rating_count=Count('ratings'),
            comment_count=Count('comments'),
            favorite_count=Count('favorites')
        ).order_by('-rating_count', '-comment_count')[:5]

        context['active_users'] = active_users

        # 30天用户注册趋势
        thirty_days_ago = timezone.now() - timedelta(days=30)
        user_signup_data = User.objects.filter(
            date_joined__gte=thirty_days_ago
        ).annotate(
            day=TruncDay('date_joined')
        ).values('day').annotate(count=Count('id')).order_by('day')

        # 转换为图表数据格式
        signup_labels = []
        signup_values = []

        for item in user_signup_data:
            signup_labels.append(item['day'].strftime('%m-%d'))
            signup_values.append(item['count'])

        context['signup_labels'] = json.dumps(signup_labels)
        context['signup_values'] = json.dumps(signup_values)

        # 返回响应
        return TemplateResponse(request, 'admin/dashboard.html', context)

    def rating_analytics_view(self, request):
        """评分数据分析视图"""
        from recommendation.models import UserRating
        from django.contrib.auth.models import User
        from django.db.models import Count, Avg
        from django.db.models.functions import TruncDay

        # 获取基础统计数据
        total_ratings = UserRating.objects.count()
        avg_rating = UserRating.objects.aggregate(avg=Avg('rating'))['avg'] or 0

        # 评分分布
        rating_distribution = (
            UserRating.objects
            .values('rating')
            .annotate(count=Count('id'))
            .order_by('rating')
        )

        # 每日评分趋势
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_ratings = (
            UserRating.objects
            .filter(timestamp__gte=thirty_days_ago)
            .annotate(day=TruncDay('timestamp'))
            .values('day')
            .annotate(count=Count('id'), avg=Avg('rating'))
            .order_by('day')
        )

        # 准备图表数据
        rating_values = []
        rating_counts = []

        for item in rating_distribution:
            rating_values.append(float(item['rating']))
            rating_counts.append(item['count'])

        daily_labels = []
        daily_counts = []
        daily_avgs = []

        for item in daily_ratings:
            daily_labels.append(item['day'].strftime('%m-%d'))
            daily_counts.append(item['count'])
            daily_avgs.append(float(item['avg']) if item['avg'] else 0)

        # 准备上下文数据
        context = {
            'title': '评分数据分析',
            'total_ratings': total_ratings,
            'avg_rating': avg_rating,

            'rating_values': json.dumps(rating_values),
            'rating_counts': json.dumps(rating_counts),

            'daily_labels': json.dumps(daily_labels),
            'daily_counts': json.dumps(daily_counts),
            'daily_avgs': json.dumps(daily_avgs),

            # 添加最受欢迎的动漫
            'top_rated_anime': (
                UserRating.objects
                .values('anime__id', 'anime__title')
                .annotate(avg_rating=Avg('rating'), count=Count('id'))
                .filter(count__gte=5)  # 至少5个评分
                .order_by('-avg_rating')[:10]
            ),

            # 添加最活跃的评分用户
            'most_active_raters': (
                UserRating.objects
                .values('user__id', 'user__username')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            ),
        }

        return TemplateResponse(request, 'admin/rating_analytics.html', context)

    def favorite_analytics_view(self, request):
        """收藏数据分析视图"""
        from recommendation.models import UserFavorite
        from django.contrib.auth.models import User
        from django.db.models import Count
        from django.db.models.functions import TruncDay

        # 获取基础统计数据
        total_favorites = UserFavorite.objects.count()
        unique_users = UserFavorite.objects.values('user').distinct().count()
        unique_anime = UserFavorite.objects.values('anime').distinct().count()

        # 每日收藏趋势
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_favorites = (
            UserFavorite.objects
            .filter(timestamp__gte=thirty_days_ago)
            .annotate(day=TruncDay('timestamp'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        # 最受收藏的动漫
        most_favorited = (
            UserFavorite.objects
            .values('anime__id', 'anime__title')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # 最活跃的收藏用户
        most_active_users = (
            UserFavorite.objects
            .values('user__id', 'user__username')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # 准备图表数据
        daily_labels = []
        daily_counts = []

        for item in daily_favorites:
            daily_labels.append(item['day'].strftime('%m-%d'))
            daily_counts.append(item['count'])

        # 最受收藏动漫的图表数据
        anime_labels = [item['anime__title'] for item in most_favorited]
        anime_counts = [item['count'] for item in most_favorited]

        # 准备上下文数据
        context = {
            'title': '收藏数据分析',
            'total_favorites': total_favorites,
            'unique_users': unique_users,
            'unique_anime': unique_anime,

            'daily_labels': json.dumps(daily_labels),
            'daily_counts': json.dumps(daily_counts),

            'anime_labels': json.dumps(anime_labels),
            'anime_counts': json.dumps(anime_counts),

            'most_favorited': most_favorited,
            'most_active_users': most_active_users,
        }

        return TemplateResponse(request, 'admin/favorite_analytics.html', context)

    def chart_data_view(self, request):
        """提供图表数据的API端点"""
        from django.http import JsonResponse
        from anime.models import Anime
        from django.contrib.auth.models import User
        from recommendation.models import UserRating

        # 获取时间范围参数
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # 获取用户注册数据
        user_data = User.objects.filter(
            date_joined__gte=start_date
        ).annotate(
            day=TruncDay('date_joined')
        ).values('day').annotate(count=Count('id')).order_by('day')

        # 获取评分数据
        rating_data = UserRating.objects.filter(
            created_at__gte=start_date
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            count=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('day')

        # 准备返回数据
        chart_data = {
            'user_registration': {
                'labels': [x['day'].strftime('%Y-%m-%d') for x in user_data],
                'values': [x['count'] for x in user_data]
            },
            'ratings': {
                'labels': [x['day'].strftime('%Y-%m-%d') for x in rating_data],
                'values': [x['count'] for x in rating_data],
                'avg_values': [float(x['avg_rating']) if x['avg_rating'] else 0 for x in rating_data]
            }
        }

        return JsonResponse(chart_data)