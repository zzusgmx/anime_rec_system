# anime/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django.contrib import messages

# 引入自定义Admin基类
from anime_rec_system.admin import BaseModelAdmin
from .models import AnimeType, Anime


# 注册动漫类型的资源类（用于导入/导出）
class AnimeTypeResource(resources.ModelResource):
    """动漫类型导入/导出资源配置"""

    class Meta:
        model = AnimeType
        fields = ('id', 'name', 'description', 'slug', 'created_at', 'updated_at')
        export_order = ('id', 'name', 'description', 'slug', 'created_at', 'updated_at')


@admin.register(AnimeType)
class AnimeTypeAdmin(BaseModelAdmin):
    """动漫类型管理界面"""
    resource_class = AnimeTypeResource

    list_display = ('name', 'slug', 'anime_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    # 字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # 只读字段
    readonly_fields = ('created_at', 'updated_at')

    def anime_count(self, obj):
        """显示该类型下的动漫数量，并链接到过滤视图"""
        count = obj.animes.count()
        url = reverse('admin:anime_anime_changelist') + f'?type__id__exact={obj.id}'
        return format_html('<a href="{}">{} 个动漫</a>', url, count)

    anime_count.short_description = '动漫数量'


# 定义动漫资源类（用于导入/导出）
class AnimeResource(resources.ModelResource):
    """动漫导入/导出资源配置"""

    class Meta:
        model = Anime
        fields = (
            'id', 'title', 'original_title', 'slug', 'description',
            'release_date', 'episodes', 'duration', 'type__name',
            'popularity', 'rating_avg', 'rating_count', 'view_count',
            'favorite_count', 'is_featured', 'is_completed',
            'created_at', 'updated_at'
        )


@admin.register(Anime)
class AnimeAdmin(BaseModelAdmin):
    """动漫管理界面"""
    resource_class = AnimeResource

    # 列表显示字段
    list_display = (
        'title', 'show_cover', 'type', 'release_date',
        'episodes', 'popularity_display', 'rating_display',
        'is_featured', 'is_completed'
    )

    # 列表过滤器
    list_filter = (
        'is_featured', 'is_completed', 'type',
        ('release_date', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('title', 'original_title', 'description')

    # 默认排序
    ordering = ('-popularity', '-release_date')

    # 每页显示记录数
    list_per_page = 20

    # 预填充字段
    prepopulated_fields = {'slug': ('title',)}

    # 可编辑列表字段
    list_editable = ('is_featured', 'is_completed')

    # 日期层次结构
    date_hierarchy = 'release_date'

    # 字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'original_title', 'slug', 'cover', 'description')
        }),
        ('详细信息', {
            'fields': ('type', 'release_date', 'episodes', 'duration')
        }),
        ('状态标识', {
            'fields': ('is_featured', 'is_completed')
        }),
        ('统计数据', {
            'classes': ('collapse',),
            'fields': ('popularity', 'rating_avg', 'rating_count', 'view_count', 'favorite_count'),
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('uuid', 'created_at', 'updated_at'),
        }),
    )

    # 只读字段
    readonly_fields = (
        'uuid', 'popularity', 'rating_avg', 'rating_count',
        'view_count', 'favorite_count', 'created_at', 'updated_at'
    )

    # 批量操作
    actions = ['make_featured', 'make_not_featured', 'mark_as_completed']

    # 自定义显示方法
    def show_cover(self, obj):
        """显示动漫封面缩略图"""
        if obj.cover:
            return format_html(
                '<img src="{}" width="50" height="70" style="object-fit: cover;" />',
                obj.cover.url
            )
        return format_html('<span style="color: #999;">无封面</span>')

    show_cover.short_description = '封面'

    def rating_display(self, obj):
        """格式化显示评分和评分数量"""
        if obj.rating_avg:
            # 创建星级显示
            stars = '★' * int(obj.rating_avg) + '☆' * (5 - int(obj.rating_avg))
            return format_html(
                '{} <span style="color:#888;">({:.1f}, {}个评分)</span>',
                stars, obj.rating_avg, obj.rating_count
            )
        return format_html('<span style="color:#999;">暂无评分</span>')

    rating_display.short_description = '评分'

    def popularity_display(self, obj):
        """格式化显示热门度"""
        # 将0-1的热门度值转换为百分比显示
        percent = int(obj.popularity * 100)

        # 根据热门度设置颜色
        if percent >= 75:
            color = 'red'
        elif percent >= 50:
            color = 'orange'
        elif percent >= 25:
            color = 'green'
        else:
            color = 'gray'

        return format_html(
            '<div style="background-color: #eee; width: 100px; height: 10px;">'
            '<div style="background-color: {}; width: {}px; height: 10px;"></div>'
            '</div><span>{:.0f}%</span>',
            color, percent, obj.popularity * 100
        )

    popularity_display.short_description = '热门度'

    # 批量操作方法
    def make_featured(self, request, queryset):
        """批量设置为推荐"""
        queryset.update(is_featured=True)
        self.message_user(request, f"成功将 {queryset.count()} 部动漫设为推荐")

    make_featured.short_description = "设置为推荐"

    def make_not_featured(self, request, queryset):
        """批量取消推荐"""
        queryset.update(is_featured=False)
        self.message_user(request, f"成功取消 {queryset.count()} 部动漫的推荐状态")

    make_not_featured.short_description = "取消推荐"

    def mark_as_completed(self, request, queryset):
        """批量标记为已完结"""
        queryset.update(is_completed=True)
        self.message_user(request, f"成功将 {queryset.count()} 部动漫标记为已完结")

    mark_as_completed.short_description = "标记为已完结"

    # 覆盖保存方法，更新slug或进行其他操作
    def save_model(self, request, obj, form, change):
        """
        保存模型时执行额外操作
        * 为新动漫设置默认值
        * 记录修改历史
        """
        # 如果是新增动漫，设置默认热门度为0
        if not change:
            obj.popularity = 0

        # 保存模型
        super().save_model(request, obj, form, change)

        # 提示成功信息
        if change:
            messages.success(request, f'动漫 "{obj.title}" 已成功更新')
        else:
            messages.success(request, f'动漫 "{obj.title}" 已成功添加')