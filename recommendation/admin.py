from django.contrib import admin

# Register your models here.

# recommendation/admin.py
from django.contrib import admin
from .models import UserRating, UserComment, UserLike, UserFavorite, RecommendationCache


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'rating', 'timestamp')
    search_fields = ('user__username', 'anime__title')
    list_filter = ('timestamp', 'rating')


@admin.register(UserComment)
class UserCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'content_preview', 'like_count', 'timestamp')
    search_fields = ('user__username', 'anime__title', 'content')
    list_filter = ('timestamp',)
    readonly_fields = ('like_count',)

    def content_preview(self, obj):
        """显示评论内容预览"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = '评论内容'


@admin.register(UserLike)
class UserLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment_preview', 'timestamp')
    search_fields = ('user__username', 'comment__content')
    list_filter = ('timestamp',)

    def comment_preview(self, obj):
        """显示被点赞评论预览"""
        return obj.comment.content[:30] + '...' if len(obj.comment.content) > 30 else obj.comment.content

    comment_preview.short_description = '评论内容'


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'timestamp')
    search_fields = ('user__username', 'anime__title')
    list_filter = ('timestamp',)


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'rec_type', 'score', 'expires_at')
    search_fields = ('user__username', 'anime__title')
    list_filter = ('rec_type', 'expires_at')
    readonly_fields = ('score',)