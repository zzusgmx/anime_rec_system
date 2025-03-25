from django.contrib import admin

# Register your models here.

# users/admin.py
from django.contrib import admin
from .models import Profile, UserBrowsing, UserPreference


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'birth_date', 'rating_count', 'comment_count')
    search_fields = ('user__username', 'user__email', 'bio')
    list_filter = ('gender',)
    readonly_fields = ('rating_count', 'comment_count')


@admin.register(UserBrowsing)
class UserBrowsingAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'browse_count', 'last_browsed')
    search_fields = ('user__username', 'anime__title')
    list_filter = ('last_browsed',)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'preference_value', 'last_updated')
    search_fields = ('user__username', 'anime__title')
    list_filter = ('last_updated',)
    readonly_fields = ('preference_value',)
