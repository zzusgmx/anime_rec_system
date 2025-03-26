# users/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import (
    LoginView, PasswordResetView,
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from rest_framework_simplejwt.tokens import RefreshToken

from .forms import (
    UserLoginForm, UserRegisterForm, UserPasswordResetForm,
    UserSetPasswordForm, ProfileUpdateForm
)
from .models import Profile


class CustomLoginView(LoginView):
    """
    自定义登录视图
    使用自定义表单并处理'记住我'功能
    """
    form_class = UserLoginForm
    template_name = 'users/login.html'

    def form_valid(self, form):
        """登录成功处理 - Web界面认证策略"""
        remember_me = form.cleaned_data.get('remember_me')

        # 如果用户不想被记住，设置会话过期时间为关闭浏览器时
        if not remember_me:
            self.request.session.set_expiry(0)

        # 不再生成JWT令牌，使用Django原生会话认证
        user = form.get_user()

        messages.success(self.request, f'欢迎回来, {user.username}!')
        return super().form_valid(form)


def custom_logout_view(request):
    """
    处理GET和POST请求的登出视图
    """
    # 清除JWT令牌
    if 'jwt_refresh' in request.session:
        del request.session['jwt_refresh']
    if 'jwt_access' in request.session:
        del request.session['jwt_access']

    # 登出用户
    logout(request)

    messages.info(request, '您已成功退出登录')
    return redirect('login')


class CustomRegisterView(CreateView):
    """
    智能环境感知的注册视图
    在开发环境自动激活，生产环境邮件验证
    """
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        """表单验证成功时处理：环境感知的用户激活策略"""
        import sys

        # 保存用户基础数据
        user = form.save(commit=False)

        # 环境感知激活策略
        if 'runserver' in sys.argv:  # 开发服务器检测
            # DEV环境：自动激活用户 - 无邮件依赖模式
            user.is_active = True  # 🔓 绕过激活锁
            user.save()

            # 生成JWT授权令牌
            refresh = RefreshToken.for_user(user)
            self.request.session['jwt_refresh'] = str(refresh)
            self.request.session['jwt_access'] = str(refresh.access_token)

            # 自动登录用户
            login(self.request, user)

            messages.success(
                self.request,
                f'DEV模式：账号 {user.username} 已自动激活并登录！'
            )
            return redirect('profile')  # 直接跳转到个人资料页
        else:
            # PROD环境：标准安全流程 - 邮件验证激活
            user.is_active = False
            user.save()
            # 发送激活邮件
            self.send_activation_email(user)
            messages.success(
                self.request,
                '注册成功！请查收邮件并点击激活链接完成账号激活。'
            )
            return redirect('login')

    def send_activation_email(self, user):
        """发送账户激活邮件"""
        current_site = get_current_site(self.request)
        mail_subject = '激活您的动漫推荐系统账号'

        # 生成验证链接
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        activation_link = f"http://{current_site.domain}/activate/{uid}/{token}/"

        # 准备邮件内容
        message = render_to_string('users/activation_email.html', {
            'user': user,
            'activation_link': activation_link,
            'site_name': current_site.name,
        })

        # 发送邮件
        email = EmailMessage(
            mail_subject, message, to=[user.email]
        )
        email.content_subtype = "html"
        email.send()


def activate_account(request, uidb64, token):
    """
    账户激活函数
    验证用户ID和令牌，激活用户账户
    """
    try:
        # 解码用户ID
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # 验证令牌
    if user is not None and default_token_generator.check_token(user, token):
        # 激活用户
        user.is_active = True
        user.save()

        # 自动登录用户
        login(request, user)

        messages.success(request, '账号激活成功！现在您可以开始使用动漫推荐系统了。')
        return redirect('profile')
    else:
        messages.error(request, '激活链接无效！请重新注册或联系管理员。')
        return redirect('register')


class CustomPasswordResetView(PasswordResetView):
    """
    自定义密码重置视图
    使用自定义表单
    """
    form_class = UserPasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """自定义密码重置完成视图"""
    template_name = 'users/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """自定义密码重置确认视图"""
    form_class = UserSetPasswordForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """自定义密码重置完成视图"""
    template_name = 'users/password_reset_complete.html'


@login_required
def profile_view(request):
    """
    用户个人资料视图
    展示和更新用户个人资料
    """
    if request.method == 'POST':
        # 处理表单提交
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, '个人资料更新成功！')
            return redirect('profile')
    else:
        # 显示表单
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'profile_form': profile_form
    }
    return render(request, 'users/profile.html', context)


# JWT API视图函数
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


class TokenObtainView(APIView):
    """
    JWT令牌获取API视图
    用于前后端分离架构中获取访问令牌
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # 验证用户
        user = authenticate(username=username, password=password)

        if user is None:
            return Response({
                'error': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # 确保用户已激活
        if not user.is_active:
            return Response({
                'error': '账户未激活，请检查您的邮箱并激活账户'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # 生成JWT令牌
        refresh = RefreshToken.for_user(user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff
            }
        })


class TokenRefreshView(APIView):
    """
    JWT令牌刷新API视图
    用于刷新过期的访问令牌
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response({
                'error': '刷新令牌不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 验证刷新令牌
            refresh = RefreshToken(refresh_token)

            return Response({
                'access': str(refresh.access_token)
            })
        except Exception as e:
            return Response({
                'error': '无效的刷新令牌'
            }, status=status.HTTP_401_UNAUTHORIZED)


class TokenVerifyView(APIView):
    """
    JWT令牌验证API视图
    用于验证访问令牌是否有效
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'message': '令牌有效',
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'is_staff': request.user.is_staff
            }
        })


class LogoutView(APIView):
    """
    注销API视图
    使JWT令牌失效
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 获取刷新令牌
            refresh_token = request.data.get('refresh')

            if refresh_token:
                # 使令牌失效
                token = RefreshToken(refresh_token)
                token.blacklist()

                return Response({
                    'message': '注销成功'
                })
            else:
                return Response({
                    'error': '刷新令牌不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)