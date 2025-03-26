# anime_rec_system/celery.py
from celery import Celery

app = Celery('anime_rec_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task
def update_recommendations(user_id):
    """量子异步更新用户推荐数据"""
    from recommendation.engine.recommendation_engine import recommendation_engine
    recommendation_engine.update_recommendations_cache(user_id)