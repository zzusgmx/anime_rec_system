from django.apps import AppConfig

class VisualizationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visualizations'
    verbose_name = '数据可视化'

    def ready(self):
        # 导入信号处理器
        import visualizations.signals