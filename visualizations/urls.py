from django.urls import path
from . import views
# 在visualizations/urls.py文件的顶部添加这些导入语句
from .views import (
    visualization_community_activity,
    visualization_user_distribution,
    visualization_discussion_stats,
    visualization_interaction_stats
)
app_name = 'visualizations'

urlpatterns = [
    # 页面路由
    path('dashboard/', views.visualization_dashboard, name='dashboard'),
    path('insights/', views.user_insights, name='insights'),
    path('community/', views.community_analysis, name='community'),  # 确保此处的函数名与views.py中的函数名一致
    path('comparison/', views.comparison_tool, name='comparison'),

    # API路由
    path('api/dashboard/save/', views.save_dashboard, name='save_dashboard'),
    path('api/dashboard/<int:dashboard_id>/set-default/', views.set_default_dashboard, name='set_default_dashboard'),
    path('api/dashboard/<int:dashboard_id>/delete/', views.delete_dashboard, name='delete_dashboard'),
    path('api/preferences/update/', views.update_visualization_preferences, name='update_preferences'),
    path('api/export/<str:chart_type>/', views.export_visualization, name='export_visualization'),

    # 数据API
    path('api/data/rating-distribution/', views.visualization_rating_distribution, name='viz_rating_distribution'),
    path('api/data/genre-preference/', views.visualization_genre_preference, name='viz_genre_preference'),
    path('api/data/viewing-trends/', views.visualization_viewing_trends, name='viz_viewing_trends'),
    path('api/data/activity-summary/', views.visualization_activity_summary, name='viz_activity_summary'),
    path('api/data/journey-timeline/', views.visualization_journey_timeline, name='viz_journey_timeline'),
    path('api/data/network-data/', views.visualization_network_data, name='viz_network_data'),
    path('api/data/recommendation-insights/', views.visualization_recommendation_insights,
         name='viz_recommendation_insights'),

    # 新增API路由
    path('api/data/community-activity/', visualization_community_activity, name='viz_community_activity'),
    path('api/data/user-distribution/', visualization_user_distribution, name='viz_user_distribution'),
    path('api/data/discussion-stats/', visualization_discussion_stats, name='viz_discussion_stats'),
    path('api/data/interaction-stats/', visualization_interaction_stats, name='viz_interaction_stats'),
]