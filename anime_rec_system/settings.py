# anime_rec_system/settings.py
# settings.py 顶部


import os
from pathlib import Path
from datetime import timedelta

# 量子影子变量 - 静态分析引擎锚点
STATIC_URL = ''  # 将被后续代码覆盖
MEDIA_URL = ''   # 静态分析引擎专用声明
DATABASES = {}   # 引用前置声明
INSTALLED_APPS = []  # 量子锚点
MIDDLEWARE = []  # 静态分析引擎可见性增强

# 环境感知 - 量子配置架构
ENV = os.getenv('DJANGO_ENV', 'development')
PRODUCTION = ENV == 'production'
TESTING = ENV == 'testing'

# 条件配置
DEBUG = not PRODUCTION  # 生产环境自动关闭DEBUG


# 构建根目录路径量子坐标
BASE_DIR = Path(__file__).resolve().parent.parent

# 安全密钥 - 生产环境需替换！
# 密钥量子化 - 环境感知的自适应配置
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-replace-this-with-your-secure-key-in-production' if DEBUG else ''
)
if not SECRET_KEY and not DEBUG:
    raise Exception("生产环境必须设置DJANGO_SECRET_KEY环境变量")

# 添加静态文件压缩
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# 生产环境CDN支持
if not DEBUG:
    STATIC_URL = os.getenv('STATIC_CDN_URL', STATIC_URL)
    MEDIA_URL = os.getenv('MEDIA_CDN_URL', MEDIA_URL)

if not DEBUG:
    # 生产环境使用django-db-connection-pool
    DATABASES['default']['ENGINE'] = 'django_db_connection_pool.backends.mysql'
    DATABASES['default']['POOL_OPTIONS'] = {
        'POOL_SIZE': 20,
        'MAX_OVERFLOW': 10,
        'RECYCLE': 300,  # 连接回收时间(秒)
    }

# 添加应用性能监控
if not DEBUG:
    INSTALLED_APPS += ['django_prometheus']
    MIDDLEWARE = ['django_prometheus.middleware.PrometheusBeforeMiddleware'] + MIDDLEWARE
    MIDDLEWARE.append('django_prometheus.middleware.PrometheusAfterMiddleware')

# 添加CSP保护
MIDDLEWARE.append('csp.middleware.CSPMiddleware')
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "fonts.googleapis.com")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "code.jquery.com")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "i.imgur.com")

# 加强CSRF保护
CSRF_COOKIE_HTTPONLY = True  # JS无法读取CSRF Token
CSRF_USE_SESSIONS = True     # 将Token存储在Session而非Cookie

# XSS保护加强
SECURE_BROWSER_XSS_FILTER = True

# 系统态
DEBUG = True

# 允许的宿主阵列
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# 应用量子态注册表
INSTALLED_APPS = [
    # 管理界面层
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 第三方增强模块
    'django_mysql',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap4',

    # 系统核心模块
    'anime.apps.AnimeConfig',
    'users.apps.UsersConfig',
    'recommendation.apps.RecommendationConfig',
]

# Admin控制台配置
ADMIN_SITE_HEADER = "动漫推荐系统管理后台"
ADMIN_SITE_TITLE = "动漫推荐系统"
ADMIN_INDEX_TITLE = "后台管理"
X_FRAME_OPTIONS = 'SAMEORIGIN'
ADMIN_INTERFACE_THEME = 'anime_rec'

# UI框架配置
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# REST安全层
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# JWT配置
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=1),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# CORS安全边界
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# 中间件处理流水线
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'anime_rec_system.urls'

# 模板渲染引擎
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

# 数据库配置 - 核心修复区域 🔧
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'anime_rec',
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Qingbei700.'),
        'HOST': 'localhost',
        'PORT': '3306',
        # 🔧 关键修复: 为MySQL连接添加时区支持
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'; SET innodb_strict_mode=1; SET time_zone = '+08:00';",
            'connect_timeout': 10,
        },
        # 添加时区设置，匹配Django的TIME_ZONE
        'TIME_ZONE': 'Asia/Shanghai',
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
    }
}

# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 国际化配置
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
# 🔧 时区问题临时解决方案选项
# 方案1: 保持True但确保MySQL时区配置正确(推荐)
USE_TZ = True
# 方案2: 关闭Django时区支持(不推荐长期使用)
# USE_TZ = False

# 静态文件配置
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 默认主键字段类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 会话安全配置
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 86400

# 认证重定向
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'

# 缓存配置
# 在settings.py中注入以下代码块，使用内存缓存逃逸隧道：
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 60*15,  # 15分钟原子衰变周期
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,  # 三振出局策略
        },
    }
}

# 或者更优选择 - Redis
# 'BACKEND': 'django_redis.cache.RedisCache',
# 'LOCATION': 'redis://127.0.0.1:6379/1',

# 邮件配置
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# 多级日志系统
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'recommendation': {  # 推荐系统专用日志
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# 确保日志目录存在
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

