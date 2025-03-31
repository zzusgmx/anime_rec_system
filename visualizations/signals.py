from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import VisualizationExport, DataCache

# 清理过期的数据缓存
@receiver(post_save, sender=DataCache)
def clean_expired_cache(sender, **kwargs):
    """清理过期的数据缓存"""
    DataCache.objects.filter(expires_at__lt=timezone.now()).delete()

# 数据导出完成后处理
@receiver(post_save, sender=VisualizationExport)
def process_visualization_export(sender, instance, created, **kwargs):
    """处理可视化导出完成事件"""
    if created:
        # 可以在这里添加导出后的处理逻辑
        # 例如：发送通知、更新统计数据等
        pass

# 清理过期的导出记录
def clean_old_exports():
    """清理30天前的导出记录"""
    threshold = timezone.now() - timedelta(days=30)
    VisualizationExport.objects.filter(created_at__lt=threshold).delete()