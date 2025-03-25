# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile


class UserLoginForm(AuthenticationForm):
    """
    用户登录表单
    继承Django内置的AuthenticationForm，添加Bootstrap样式
    """
    username = forms.CharField(
        label="用户名",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入用户名',
                'autofocus': True
            }
        )
    )

    password = forms.CharField(
        label="密码",
        strip=False,  # 保留前后空格，避免密码错误
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入密码'
            }
        )
    )

    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input'
            }
        )
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class UserRegisterForm(UserCreationForm):
    """
    用户注册表单
    继承Django内置的UserCreationForm，添加额外字段
    """
    email = forms.EmailField(
        label="电子邮箱",
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入有效的电子邮箱'
            }
        )
    )

    username = forms.CharField(
        label="用户名",
        min_length=4,
        max_length=30,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入4-30位用户名'
            }
        )
    )

    password1 = forms.CharField(
        label="密码",
        strip=False,
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入密码（至少8位）'
            }
        )
    )

    password2 = forms.CharField(
        label="确认密码",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请再次输入密码'
            }
        )
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        """验证邮箱是否已被注册"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("该邮箱已被注册")
        return email

    def clean_username(self):
        """验证用户名是否合法"""
        username = self.cleaned_data.get('username')

        # 检查用户名是否只包含字母、数字和下划线
        if not username.isalnum() and '_' not in username:
            raise ValidationError("用户名只能包含字母、数字和下划线")

        return username


class UserPasswordResetForm(PasswordResetForm):
    """
    忘记密码表单
    继承Django内置的PasswordResetForm，添加Bootstrap样式
    """
    email = forms.EmailField(
        label="电子邮箱",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入您注册时使用的电子邮箱',
                'autocomplete': 'email'
            }
        )
    )


class UserSetPasswordForm(SetPasswordForm):
    """
    设置新密码表单
    继承Django内置的SetPasswordForm，添加Bootstrap样式
    """
    new_password1 = forms.CharField(
        label="新密码",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请输入新密码',
                'autocomplete': 'new-password'
            }
        )
    )

    new_password2 = forms.CharField(
        label="确认新密码",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '请再次输入新密码',
                'autocomplete': 'new-password'
            }
        )
    )


class ProfileUpdateForm(forms.ModelForm):
    """
    用户档案更新表单
    用于更新Profile模型的扩展用户信息
    """
    avatar = forms.ImageField(
        label="头像",
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'form-control'
            }
        )
    )

    bio = forms.CharField(
        label="个人简介",
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '介绍一下自己吧'
            }
        )
    )

    birth_date = forms.DateField(
        label="出生日期",
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date'  # HTML5日期选择器
            }
        )
    )

    gender = forms.ChoiceField(
        label="性别",
        required=False,
        choices=[('', '请选择'), ('male', '男'), ('female', '女'), ('other', '其他')],
        widget=forms.Select(
            attrs={
                'class': 'form-control'
            }
        )
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'birth_date', 'gender']