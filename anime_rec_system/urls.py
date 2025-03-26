# anime_rec_system/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from anime_rec_system.admin import DashboardAdmin

# 创建自定义Admin站点实例
admin_site = DashboardAdmin(name='dashboard_admin')

# 注册相同的模型到自定义admin站点
from django.apps import apps

for model, model_admin in admin.site._registry.items():
    admin_site.register(model, model_admin.__class__)

urlpatterns = [
    # 默认Django管理后台
    path('admin/', admin_site.urls),

    # 用户认证路由
    path('', include('users.urls')),

    # API路由
    #path('api/', include('anime.urls')),

    # 主页重定向
    path('', RedirectView.as_view(url='/login/', permanent=False)),
]

# 开发环境中提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)