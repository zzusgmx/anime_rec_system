# anime_rec_system/settings.py

import os
from pathlib import Path

# 构建基础路径：项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 安全密钥 - 生产环境需替换！
SECRET_KEY = 'django-insecure-replace-this-with-your-secure-key-in-production'

# 调试模式 - 生产环境设为False
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# 应用定义
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 第三方应用
    'django_mysql',  # MySQL扩展功能
    
    # 自定义应用
    'anime.apps.AnimeConfig',
    'users.apps.UsersConfig',
    'recommendation.apps.RecommendationConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'anime_rec_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'anime_rec_system.wsgi.application'

# 数据库配置 - 使用MySQL + 连接池优化
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'anime_rec',
        'USER': 'anime_user',
        'PASSWORD': 'Qingbei700.',  # 生产环境使用环境变量
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            # MySQL会话配置
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            # innodb_strict_mode防止数据截断
            'init_command': "SET innodb_strict_mode=1",
            # 连接超时设置
            'connect_timeout': 10,
        },
        # 连接池配置 - 性能优化
        'CONN_MAX_AGE': 600,  # 连接保持600秒
        'CONN_HEALTH_CHECKS': True,  # 启用连接健康检查
        'OPTIONS': {
            # 使用持久连接
            'charset': 'utf8mb4',
        },
    }
}

# 密码验证配置
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # 最小密码长度
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 国际化配置
LANGUAGE_CODE = 'zh-hans'  # 中文界面
TIME_ZONE = 'Asia/Shanghai'  # 中国时区
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 静态文件配置
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 默认主键字段类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 会话配置 - 安全加固
SESSION_COOKIE_SECURE = False  # 开发环境设为False，生产环境为True（需HTTPS）
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # 关闭浏览器时结束会话
SESSION_COOKIE_AGE = 86400  # 会话过期时间（秒）

# 登录重定向URL
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

# 缓存配置 - 开发环境使用本地内存缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-cache-key',
    }
}

# 邮件配置 - 用于密码重置功能
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # 开发环境
# 生产环境使用SMTP：
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.example.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your_email@example.com'
# EMAIL_HOST_PASSWORD = 'your_password'