# users/urls.py 中的登出URL配置

from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    # 基于表单的认证视图 - 用于Web界面
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout_view, name='logout'),  # 确保函数名与views.py中定义一致
    path('register/', views.CustomRegisterView.as_view(), name='register'),
    path('profile/', views.profile_view, name='profile'),
    # JWT测试页面
    path('jwt-test/', TemplateView.as_view(template_name='users/jwt_test.html'), name='jwt_test'),
    # 账户激活
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),

    # 密码重置流程
    path('password-reset/',
         views.CustomPasswordResetView.as_view(),
         name='password_reset'),
    path('password-reset/done/',
         views.CustomPasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         views.CustomPasswordResetCompleteView.as_view(),
         name='password_reset_complete'),

    # JWT认证API端点 - 用于前后端分离架构
    path('api/token/', views.TokenObtainView.as_view(), name='token_obtain'),
    path('api/token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', views.TokenVerifyView.as_view(), name='token_verify'),
    path('api/logout/', views.LogoutView.as_view(), name='api_logout'),
]