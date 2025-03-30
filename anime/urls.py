# anime/urls.py

from django.urls import path, re_path
from . import views

app_name = 'anime'

urlpatterns = [
    # 1. 首先定义静态路径 - 精确匹配
    path('', views.anime_list, name='anime_list'),
    path('create/', views.anime_create, name='anime_create'),

    # 恢复原有搜索视图的URL名称
    path('search/', views.anime_search, name='anime_search'),

    # 添加ID专用搜索路径 - 使用不同的URL模式
    path('find-by-id/<int:anime_id>/', views.anime_find_by_id, name='anime_find_by_id'),

    path('not-found/', views.anime_not_found, name='anime_not_found'),

    # 其他路由保持不变
    path('rate/<int:anime_id>/', views.rate_anime, name='rate_anime'),
    path('favorite/<int:anime_id>/', views.toggle_favorite, name='toggle_favorite'),
    re_path(r'^(?P<slug>[\w-]+)/comments/$', views.anime_comments, name='anime_comments'),

    path('types/', views.anime_type_list, name='anime_type_list'),

    path('types/create/', views.anime_type_create, name='anime_type_create'),
    # 量子级修复：添加紧急修复slug的路由
    path('types/fix-slug/', views.fix_type_slug, name='fix_type_slug'),
    path('types/<slug:slug>/edit/', views.anime_type_edit, name='anime_type_edit'),
    path('types/<slug:slug>/delete/', views.anime_type_delete, name='anime_type_delete'),
    re_path(r'^types/(?P<slug>[\w-]+)/$', views.anime_by_type, name='anime_by_type'),

    path('<slug:slug>/edit/', views.anime_edit, name='anime_edit'),
    path('<slug:slug>/delete/', views.anime_delete, name='anime_delete'),
    re_path(r'^(?P<slug>[\w-]+)/$', views.anime_detail, name='anime_detail'),
]