from django.db import models
from django.contrib.auth.models import User
from anime.models import Anime
import json


class VisualizationPreference(models.Model):
    """用户可视化偏好设置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='visualization_pref')
    theme = models.CharField(max_length=50, default='quantum')  # 可视化主题
    default_view = models.CharField(max_length=50, default='overview')  # 默认视图
    chart_types = models.JSONField(default=dict)  # 各类图表的偏好设置
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_chart_preference(self, chart_type):
        """获取特定图表类型的偏好"""
        if not self.chart_types:
            return {}
        return self.chart_types.get(chart_type, {})

    def set_chart_preference(self, chart_type, preferences):
        """设置特定图表类型的偏好"""
        if not self.chart_types:
            self.chart_types = {}
        self.chart_types[chart_type] = preferences
        self.save(update_fields=['chart_types'])

    class Meta:
        verbose_name = '可视化偏好'
        verbose_name_plural = '可视化偏好'


class DataCache(models.Model):
    """可视化数据缓存"""
    cache_key = models.CharField(max_length=255, unique=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = '数据缓存'
        verbose_name_plural = '数据缓存'
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at'])
        ]


class CustomDashboard(models.Model):
    """用户自定义仪表盘"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboards')
    name = models.CharField(max_length=100)
    layout = models.JSONField(default=dict)  # 仪表盘布局配置
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_widgets(self):
        """获取仪表盘组件列表"""
        return self.layout.get('widgets', [])

    def add_widget(self, widget_config):
        """添加组件到仪表盘"""
        if not self.layout:
            self.layout = {'widgets': []}
        self.layout['widgets'].append(widget_config)
        self.save(update_fields=['layout'])

    class Meta:
        verbose_name = '自定义仪表盘'
        verbose_name_plural = '自定义仪表盘'
        unique_together = [('user', 'name')]


class VisualizationExport(models.Model):
    """可视化导出记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visualization_exports')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    format = models.CharField(max_length=20)  # PDF, PNG, SVG, JSON等
    file_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '可视化导出'
        verbose_name_plural = '可视化导出'
        ordering = ['-created_at']