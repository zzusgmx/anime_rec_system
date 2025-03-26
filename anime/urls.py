# anime/urls.py

from django.urls import path, re_path
from . import views

app_name = 'anime'

urlpatterns = [
    # 1. 首先定义静态路径 - 精确匹配
    path('', views.anime_list, name='anime_list'),
    path('create/', views.anime_create, name='anime_create'),
    path('search/', views.anime_search, name='anime_search'),
    path('not-found/', views.anime_not_found, name='anime_not_found'),  # 新增: 404优雅降级页面

    # 新增用户交互API
    path('rate/<int:anime_id>/', views.rate_anime, name='rate_anime'),
    path('favorite/<int:anime_id>/', views.toggle_favorite, name='toggle_favorite'),

    # 2. 类型相关的路径 - 避免它们被动漫slug捕获
    path('types/', views.anime_type_list, name='anime_type_list'),
    path('types/create/', views.anime_type_create, name='anime_type_create'),
    path('types/fix-slug/', views.fix_type_slug, name='fix_type_slug'),  # 新增: 修复空slug的API端点
    path('types/<slug:slug>/edit/', views.anime_type_edit, name='anime_type_edit'),
    path('types/<slug:slug>/delete/', views.anime_type_delete, name='anime_type_delete'),
    re_path(r'^types/(?P<slug>[\w-]+)/$', views.anime_by_type, name='anime_by_type'),  # 改用regex增强匹配能力

    # 3. 最后是带参数的动漫路径 - 这些路径最通用，放在最后防止URL碰撞
    path('<slug:slug>/edit/', views.anime_edit, name='anime_edit'),
    path('<slug:slug>/delete/', views.anime_delete, name='anime_delete'),
    # 使用正则表达式模式增强匹配能力 - 捕获更广范围的slug变体
    re_path(r'^(?P<slug>[\w-]+)/$', views.anime_detail, name='anime_detail'),
]