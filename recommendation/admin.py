# recommendation/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Count, Avg
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django.template.response import TemplateResponse
from django.db.models.functions import TruncDay, TruncMonth
import json
from datetime import datetime, timedelta
from django.utils import timezone

# 引入自定义Admin基类
from anime_rec_system.admin import BaseModelAdmin
from .models import (
    UserRating, UserComment, UserLike,
    UserFavorite, RecommendationCache
)


# 评分资源类（用于导入/导出）
class UserRatingResource(resources.ModelResource):
    """用户评分导入/导出资源配置"""

    class Meta:
        model = UserRating
        fields = ('id', 'user__username', 'anime__title', 'rating', 'timestamp', 'created_at')


@admin.register(UserRating)
class UserRatingAdmin(BaseModelAdmin):
    """用户评分管理界面"""
    resource_class = UserRatingResource

    # 列表显示字段
    list_display = ('user', 'anime', 'rating_display', 'timestamp')

    # 列表过滤器
    list_filter = (
        ('timestamp', DateRangeFilter),
        'rating',
    )

    # 搜索字段
    search_fields = ('user__username', 'anime__title')

    # 默认排序
    ordering = ('-timestamp',)

    # 每页显示记录数
    list_per_page = 30

    # 自定义URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('rating-analytics/',
                 self.admin_site.admin_view(self.rating_analytics_view),
                 name='rating-analytics'),
        ]
        return custom_urls + urls

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'timestamp')

    # 字段集
    fieldsets = (
        ('评分信息', {
            'fields': ('user', 'anime', 'rating', 'timestamp')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # 自定义显示方法
    def rating_display(self, obj):
        """星级显示评分"""
        stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
        return format_html(
            '<span style="color: #ff9900;">{}</span> <span style="color: #666;">({:.1f})</span>',
            stars, obj.rating
        )

    rating_display.short_description = '评分'

    # 评分分析视图
    def rating_analytics_view(self, request):
        """评分数据分析视图"""
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


# 评论资源类（用于导入/导出）
class UserCommentResource(resources.ModelResource):
    """用户评论导入/导出资源配置"""

    class Meta:
        model = UserComment
        fields = ('id', 'user__username', 'anime__title', 'content', 'like_count', 'timestamp', 'created_at')


@admin.register(UserComment)
class UserCommentAdmin(BaseModelAdmin):
    """用户评论管理界面"""
    resource_class = UserCommentResource

    # 列表显示字段
    list_display = ('user', 'anime', 'content_preview', 'like_count', 'timestamp')

    # 列表过滤器
    list_filter = (
        ('timestamp', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('user__username', 'anime__title', 'content')

    # 默认排序
    ordering = ('-timestamp',)

    # 每页显示记录数
    list_per_page = 30

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'timestamp', 'like_count')

    # 字段集
    fieldsets = (
        ('评论信息', {
            'fields': ('user', 'anime', 'content', 'like_count', 'timestamp')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # 自定义显示方法
    def content_preview(self, obj):
        """显示评论内容预览"""
        max_length = 50
        if len(obj.content) > max_length:
            return obj.content[:max_length] + '...'
        return obj.content

    content_preview.short_description = '评论内容'

    # 自定义操作
    actions = ['approve_comments', 'delete_selected_with_confirmation']

    def approve_comments(self, request, queryset):
        """批量审核通过评论（如果实现了评论审核功能）"""
        # 如果实现了审核功能，可以在这里处理
        self.message_user(request, f"已批量审核 {queryset.count()} 条评论")

    approve_comments.short_description = "批准所选评论"

    def delete_selected_with_confirmation(self, request, queryset):
        """删除选中的评论（带确认）"""
        # 实际删除逻辑与delete_selected相同
        # 但可以在此添加确认步骤
        for obj in queryset:
            obj.delete()
        self.message_user(request, f"已删除 {queryset.count()} 条评论")

    delete_selected_with_confirmation.short_description = "删除所选评论"


# 点赞资源类（用于导入/导出）
class UserLikeResource(resources.ModelResource):
    """用户点赞导入/导出资源配置"""

    class Meta:
        model = UserLike
        fields = ('id', 'user__username', 'comment__id', 'comment__content', 'timestamp', 'created_at')


@admin.register(UserLike)
class UserLikeAdmin(BaseModelAdmin):
    """用户点赞管理界面"""
    resource_class = UserLikeResource

    # 列表显示字段
    list_display = ('user', 'comment_preview', 'comment_anime', 'timestamp')

    # 列表过滤器
    list_filter = (
        ('timestamp', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('user__username', 'comment__content')

    # 默认排序
    ordering = ('-timestamp',)

    # 每页显示记录数
    list_per_page = 30

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'timestamp')

    # 字段集
    fieldsets = (
        ('点赞信息', {
            'fields': ('user', 'comment', 'timestamp')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # 自定义显示方法
    def comment_preview(self, obj):
        """显示被点赞评论预览"""
        max_length = 30
        if len(obj.comment.content) > max_length:
            preview = obj.comment.content[:max_length] + '...'
        else:
            preview = obj.comment.content

        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:recommendation_usercomment_change', args=[obj.comment.id]),
            preview
        )

    comment_preview.short_description = '评论内容'

    def comment_anime(self, obj):
        """显示评论所属动漫"""
        return obj.comment.anime

    comment_anime.short_description = '动漫'


# 收藏资源类（用于导入/导出）
class UserFavoriteResource(resources.ModelResource):
    """用户收藏导入/导出资源配置"""

    class Meta:
        model = UserFavorite
        fields = ('id', 'user__username', 'anime__title', 'timestamp', 'created_at')


@admin.register(UserFavorite)
class UserFavoriteAdmin(BaseModelAdmin):
    """用户收藏管理界面"""
    resource_class = UserFavoriteResource

    # 列表显示字段
    list_display = ('user', 'anime', 'timestamp')

    # 列表过滤器
    list_filter = (
        ('timestamp', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('user__username', 'anime__title')

    # 默认排序
    ordering = ('-timestamp',)

    # 每页显示记录数
    list_per_page = 30

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'timestamp')

    # 字段集
    fieldsets = (
        ('收藏信息', {
            'fields': ('user', 'anime', 'timestamp')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # 自定义URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('favorite-analytics/',
                 self.admin_site.admin_view(self.favorite_analytics_view),
                 name='favorite-analytics'),
        ]
        return custom_urls + urls

    # 收藏分析视图
    def favorite_analytics_view(self, request):
        """收藏数据分析视图"""
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


# 推荐缓存资源类（用于导入/导出）
class RecommendationCacheResource(resources.ModelResource):
    """推荐缓存导入/导出资源配置"""

    class Meta:
        model = RecommendationCache
        fields = ('id', 'user__username', 'anime__title', 'score', 'rec_type', 'expires_at', 'created_at')


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(BaseModelAdmin):
    """推荐缓存管理界面"""
    resource_class = RecommendationCacheResource

    # 列表显示字段
    list_display = ('user', 'anime', 'rec_type', 'score_display', 'expires_status')

    # 列表过滤器
    list_filter = (
        'rec_type',
        ('expires_at', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('user__username', 'anime__title')

    # 默认排序
    ordering = ('-score',)

    # 每页显示记录数
    list_per_page = 30

    # 只读字段
    readonly_fields = ('created_at', 'updated_at')

    # 字段集
    fieldsets = (
        ('推荐信息', {
            'fields': ('user', 'anime', 'score', 'rec_type', 'expires_at')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # 自定义显示方法
    def score_display(self, obj):
        """格式化显示推荐分数"""
        # 根据推荐分数设置颜色
        if obj.score >= 0.7:
            color = 'green'
        elif obj.score >= 0.4:
            color = 'blue'
        else:
            color = 'gray'

        # 显示为百分比
        percent = int(obj.score * 100)

        return format_html(
            '<div style="background-color: #eee; width: 100px; height: 10px;">'
            '<div style="background-color: {}; width: {}px; height: 10px;"></div>'
            '</div><span>{:.0f}%</span>',
            color, percent, obj.score * 100
        )

    score_display.short_description = '推荐分数'

    def expires_status(self, obj):
        """显示过期状态"""
        now = timezone.now()

        if obj.expires_at < now:
            return format_html('<span style="color: red;">已过期</span>')

        # 计算剩余时间
        time_left = obj.expires_at - now
        hours_left = time_left.total_seconds() / 3600

        if hours_left < 1:
            minutes_left = time_left.total_seconds() / 60
            return format_html('<span style="color: orange;">剩余 {:.0f} 分钟</span>', minutes_left)
        elif hours_left < 24:
            return format_html('<span style="color: green;">剩余 {:.1f} 小时</span>', hours_left)
        else:
            days_left = hours_left / 24
            return format_html('<span style="color: green;">剩余 {:.1f} 天</span>', days_left)

    expires_status.short_description = '过期状态'

    # 批量操作
    actions = ['refresh_recommendations', 'clear_expired_recommendations']

    def refresh_recommendations(self, request, queryset):
        """刷新推荐缓存"""
        # 更新过期时间为当前时间+1天
        new_expire = timezone.now() + timedelta(days=1)
        queryset.update(expires_at=new_expire)
        self.message_user(request, f"已刷新 {queryset.count()} 条推荐缓存")

    refresh_recommendations.short_description = "刷新所选推荐"

    def clear_expired_recommendations(self, request, queryset):
        """清除过期推荐"""
        now = timezone.now()
        expired_count = queryset.filter(expires_at__lt=now).count()
        queryset.filter(expires_at__lt=now).delete()
        self.message_user(request, f"已清除 {expired_count} 条过期推荐缓存")

    clear_expired_recommendations.short_description = "清除过期推荐"