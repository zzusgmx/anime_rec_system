# recommendation/urls.py

from django.urls import path
from . import views

app_name = 'recommendation'

urlpatterns = [
    # 现有的URL保持不变
    # 推荐页面
    path('', views.get_recommendations, name='recommendations'),

    # 推荐API
    path('api/recommendations/', views.RecommendationAPIView.as_view(), name='api_recommendations'),
    path('user-interactions/', views.user_interactions, name='user_interactions'),
    path('user-interactions/network/', views.user_interaction_network, name='user_interaction_network'),
    # 评论回复API
    path('comments/reply/<int:comment_id>/', views.add_comment_reply, name='add_comment_reply'),
    path('comments/replies/<int:comment_id>/', views.get_comment_replies, name='get_comment_replies'),
    # 用户互动统计
    path('api/interactions/summary/', views.user_interaction_summary, name='user_interaction_summary'),
    path('api/interactions/recent/', views.recent_interactions, name='recent_interactions'),
    path('api/interactions/top-users/', views.top_interactive_users, name='top_interactive_users'),
    path('api/interactions/detail/<int:interaction_id>/', views.interaction_detail, name='interaction_detail'),
    # 用户仪表板
    path('dashboard/', views.user_activity_dashboard, name='user_dashboard'),
    # 仪表板API端点
    path('api/dashboard/recommendations/', views.dashboard_recommendations_api, name='dashboard_recommendations_api'),
    path('api/dashboard/ratings/', views.dashboard_ratings_api, name='dashboard_ratings_api'),
    path('api/dashboard/comments/', views.dashboard_comments_api, name='dashboard_comments_api'),

    # 用户收藏页面
    path('favorites/', views.user_favorites, name='favorites'),
    path('favorite/<int:anime_id>/', views.toggle_favorite, name='toggle_favorite'),

    # 浏览历史
    path('browsing-history/', views.browsing_history, name='browsing_history'),
    path('browsing-history/remove/<int:history_id>/', views.remove_history, name='remove_history'),
    path('browsing-history/clear/', views.clear_history, name='clear_history'),

    path('user-comments/', views.user_comments, name='user_comments'),  # 评论列表页面
    # 评论系统API
    path('comments/add/<int:anime_id>/', views.add_comment, name='add_comment'),
    path('comments/update/<int:comment_id>/', views.update_comment, name='update_comment'),
    path('comments/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('comments/like/<int:comment_id>/', views.toggle_like_comment, name='toggle_like_comment'),

    # 心形评分系统API
    path('heart-rating/<int:anime_id>/', views.heart_rating, name='heart_rating'),

    path('user-ratings/', views.user_ratings, name='user_ratings'),
    path('api/dashboard/likes/', views.dashboard_likes_api, name='dashboard_likes_api'),
    path('anime/like/<int:anime_id>/', views.toggle_anime_like, name='toggle_anime_like'),
    # 添加到recommendation/urls.py的urlpatterns列表
    path('api/dashboard/seasonal/', views.dashboard_seasonal_api, name='dashboard_seasonal_api'),
    path('api/dashboard/similar/', views.dashboard_similar_api, name='dashboard_similar_api'),
    path('api/dashboard/classics/', views.dashboard_classics_api, name='dashboard_classics_api'),
    path('user-likes/', views.user_likes, name='user_likes'),

]