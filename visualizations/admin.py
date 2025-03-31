from django.contrib import admin
from .models import VisualizationPreference, DataCache, CustomDashboard, VisualizationExport

@admin.register(VisualizationPreference)
class VisualizationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'default_view', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('theme', 'default_view')

@admin.register(DataCache)
class DataCacheAdmin(admin.ModelAdmin):
    list_display = ('cache_key', 'created_at', 'expires_at')
    search_fields = ('cache_key',)
    list_filter = ('created_at', 'expires_at')

@admin.register(CustomDashboard)
class CustomDashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_default', 'created_at', 'updated_at')
    search_fields = ('name', 'user__username')
    list_filter = ('is_default', 'created_at')

@admin.register(VisualizationExport)
class VisualizationExportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'format', 'created_at')
    search_fields = ('title', 'user__username')
    list_filter = ('format', 'created_at')