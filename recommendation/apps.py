from django.apps import AppConfig


class RecommendationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommendation'
<<<<<<< HEAD

    def ready(self):
        # 导入信号处理器
        import recommendation.signals
=======
>>>>>>> d1322bd2ac3da5307a056d58f203a84a82102da1
