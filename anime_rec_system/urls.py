# anime_rec_system/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from anime_rec_system.admin import DashboardAdmin
from users.views import custom_logout_view

# 创建自定义Admin站点实例
admin_site = DashboardAdmin(name='dashboard_admin')

# 注册相同的模型到自定义admin站点
from django.apps import apps

for model, model_admin in admin.site._registry.items():
    admin_site.register(model, model_admin.__class__)

urlpatterns = [
    # 注意顺序：自定义登出路由必须在admin路由之前
    path('admin/logout/', custom_logout_view, name='admin_logout'),

    # 默认Django管理后台
    path('admin/', admin_site.urls),

    # 用户认证路由
    path('', include('users.urls')),

    # 动漫应用路由
    path('anime/', include('anime.urls', namespace='anime')),

    # 推荐应用路由
    path('recommendations/', include('recommendation.urls', namespace='recommendation')),

    # 主页重定向 - 临时改为动漫列表页
    path('', RedirectView.as_view(url='/anime/', permanent=False)),
]

# 开发环境中提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)