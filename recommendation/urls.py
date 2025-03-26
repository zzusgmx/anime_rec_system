# recommendation/urls.py

from django.urls import path
from . import views

app_name = 'recommendation'

urlpatterns = [
    # 推荐页面
    path('', views.get_recommendations, name='recommendations'),

    # 推荐API
    path('api/recommendations/', views.RecommendationAPIView.as_view(), name='api_recommendations'),

    # 用户仪表板
    path('dashboard/', views.user_activity_dashboard, name='user_dashboard'),
]