from django.apps import AppConfig


class RecommendationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommendation'

    def ready(self):
        # 导入信号处理器
        import recommendation.signals

