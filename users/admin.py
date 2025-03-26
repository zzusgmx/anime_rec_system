# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from import_export import resources

# 引入自定义Admin基类
from anime_rec_system.admin import BaseModelAdmin, ActiveUserFilter
from .models import Profile, UserBrowsing, UserPreference


# 创建内联Profile管理
class ProfileInline(admin.StackedInline):
    """用户资料内联编辑"""
    model = Profile
    can_delete = False
    verbose_name_plural = '用户资料'

    # 显示的字段
    fields = (
        ('avatar', 'gender', 'birth_date'),
        'bio',
        ('rating_count', 'comment_count'),
        'preferred_types',
    )

    readonly_fields = ('rating_count', 'comment_count')

    # 自定义过滤显示
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """为多对多字段自定义过滤显示"""
        if db_field.name == "preferred_types":
            kwargs["queryset"] = db_field.remote_field.model.objects.all().order_by('name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# 自定义用户管理类
class UserAdmin(BaseUserAdmin):
    """扩展用户管理界面"""
    inlines = (ProfileInline,)

    # 列表显示字段
    list_display = (
        'username', 'email', 'display_avatar', 'display_activity',
        'is_active', 'is_staff', 'date_joined', 'last_login'
    )

    # 列表过滤器
    list_filter = (
        'is_active', 'is_staff', 'is_superuser',
        ActiveUserFilter,
        ('date_joined', DateRangeFilter),
        ('last_login', DateRangeFilter),
    )

    # 每页显示记录数
    list_per_page = 25

    # 日期层次结构
    date_hierarchy = 'date_joined'

    # 添加用户字段集
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    # 修改用户字段集
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('first_name', 'last_name', 'email')}),
        ('权限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )

    # 可搜索字段
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # 只读字段
    readonly_fields = ('last_login', 'date_joined')

    # 自定义操作
    actions = ['activate_users', 'deactivate_users']

    # 自定义显示方法
    def display_avatar(self, obj):
        """显示用户头像"""
        try:
            if obj.profile.avatar:
                return format_html(
                    '<img src="{}" width="30" height="30" style="border-radius: 50%;" />',
                    obj.profile.avatar.url
                )
        except:
            pass
        return format_html('<span style="color: #999;">无头像</span>')

    display_avatar.short_description = '头像'

    def display_activity(self, obj):
        """显示用户活跃度"""
        from recommendation.models import UserRating, UserComment

        # 查询用户活动统计
        ratings = UserRating.objects.filter(user=obj).count()
        comments = UserComment.objects.filter(user=obj).count()

        # 如果没有任何活动
        if ratings == 0 and comments == 0:
            return format_html('<span style="color: #999;">不活跃</span>')

        # 根据活动总数确定活跃度
        activity = ratings + comments

        if activity > 20:
            color = 'green'
            level = '高活跃'
        elif activity > 5:
            color = 'orange'
            level = '中活跃'
        else:
            color = 'blue'
            level = '低活跃'

        return format_html(
            '<span style="color: {};">{}</span> '
            '<span style="color: #666;">(评分: {}, 评论: {})</span>',
            color, level, ratings, comments
        )

    display_activity.short_description = '活跃度'

    # 批量操作方法
    def activate_users(self, request, queryset):
        """批量激活用户"""
        queryset.update(is_active=True)
        self.message_user(request, f"成功激活 {queryset.count()} 个用户账号")

    activate_users.short_description = "激活所选用户"

    def deactivate_users(self, request, queryset):
        """批量停用用户"""
        # 防止停用自己
        if request.user.id in queryset.values_list('id', flat=True):
            self.message_user(request, "您不能停用自己的账号", level='error')
            return

        # 防止停用超级管理员
        if queryset.filter(is_superuser=True).exists():
            self.message_user(request, "您不能停用超级管理员账号", level='error')
            return

        queryset.update(is_active=False)
        self.message_user(request, f"成功停用 {queryset.count()} 个用户账号")

    deactivate_users.short_description = "停用所选用户"


# 用户浏览资源类（用于导入/导出）
class UserBrowsingResource(resources.ModelResource):
    """用户浏览记录导入/导出资源配置"""

    class Meta:
        model = UserBrowsing
        fields = ('id', 'user__username', 'anime__title', 'browse_count', 'last_browsed', 'created_at')


@admin.register(UserBrowsing)
class UserBrowsingAdmin(BaseModelAdmin):
    """用户浏览记录管理界面"""
    resource_class = UserBrowsingResource

    # 列表显示字段
    list_display = ('user', 'anime', 'browse_count', 'last_browsed')

    # 列表过滤器
    list_filter = (
        'last_browsed',
        ('last_browsed', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('user__username', 'anime__title')

    # 默认排序
    ordering = ('-last_browsed',)

    # 每页显示记录数
    list_per_page = 30

    # 只读字段
    readonly_fields = ('created_at', 'updated_at')

    # 字段集
    fieldsets = (
        ('浏览信息', {
            'fields': ('user', 'anime', 'browse_count', 'last_browsed')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )


# 用户偏好资源类（用于导入/导出）
class UserPreferenceResource(resources.ModelResource):
    """用户偏好导入/导出资源配置"""

    class Meta:
        model = UserPreference
        fields = ('id', 'user__username', 'anime__title', 'preference_value', 'last_updated', 'created_at')


@admin.register(UserPreference)
class UserPreferenceAdmin(BaseModelAdmin):
    """用户偏好管理界面"""
    resource_class = UserPreferenceResource

    # 列表显示字段
    list_display = ('user', 'anime', 'preference_value_display', 'last_updated')

    # 列表过滤器
    list_filter = (
        ('last_updated', DateRangeFilter),
    )

    # 搜索字段
    search_fields = ('user__username', 'anime__title')

    # 默认排序
    ordering = ('-preference_value',)

    # 每页显示记录数
    list_per_page = 30

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'last_updated')

    # 字段集
    fieldsets = (
        ('偏好信息', {
            'fields': ('user', 'anime', 'preference_value', 'last_updated')
        }),
        ('元数据', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def preference_value_display(self, obj):
        """格式化显示偏好值"""
        # 将0-100的偏好值转换为百分比显示
        percent = int(obj.preference_value)

        # 根据偏好值设置颜色
        if percent >= 75:
            color = 'green'
        elif percent >= 50:
            color = 'blue'
        elif percent >= 25:
            color = 'orange'
        else:
            color = 'gray'

        return format_html(
            '<div style="background-color: #eee; width: 100px; height: 10px;">'
            '<div style="background-color: {}; width: {}px; height: 10px;"></div>'
            '</div><span>{:.0f}%</span>',
            color, percent, obj.preference_value
        )

    preference_value_display.short_description = '偏好值'


# 重新注册User模型，替换默认的管理界面
admin.site.unregister(User)
admin.site.register(User, UserAdmin)