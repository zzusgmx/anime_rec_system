from django.contrib import admin

# Register your models here.
<<<<<<< HEAD

# anime/admin.py
from django.contrib import admin
from .models import AnimeType, Anime


@admin.register(AnimeType)
class AnimeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Anime)
class AnimeAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'release_date', 'popularity', 'rating_avg', 'is_featured')
    list_filter = ('type', 'is_featured', 'is_completed')
    search_fields = ('title', 'original_title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('uuid', 'popularity', 'rating_avg', 'rating_count', 'view_count', 'favorite_count')
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'original_title', 'slug', 'uuid', 'description', 'cover')
        }),
        ('分类信息', {
            'fields': ('type', 'release_date', 'episodes', 'duration')
        }),
        ('统计信息', {
            'fields': ('popularity', 'rating_avg', 'rating_count', 'view_count', 'favorite_count')
        }),
        ('状态标识', {
            'fields': ('is_featured', 'is_completed')
        }),
    )
=======
>>>>>>> d1322bd2ac3da5307a056d58f203a84a82102da1
