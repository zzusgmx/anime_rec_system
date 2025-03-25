# anime_rec_system/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),
    
    # 用户认证路由
    path('', include('users.urls')),
    
    # API路由 - 将在后续实现
    #path('api/', include('anime.urls')),
    
    # 主页重定向 (临时，后续会实现真正的首页)
    path('', RedirectView.as_view(url='/login/', permanent=False)),
]

# 开发环境中提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)