from pathlib import Path
import os

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv()


# Security settings
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-+hi)_oc5b4amw)o&%mk__mykl=5#v9f8lyf1oy1of%7$cg3z2(')  # Use an environment variable in production
DEBUG = True
# ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '192.168.0.174', '192.168.0.150']
ALLOWED_HOSTS = ['*']  # Add your domain or IP address here
# ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# CORS - Not needed since frontend and backend are on the same domain
# Remove CORS settings
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000", 
    "http://localhost:8000", 
     "*" # Allow requests from React frontend Add on
]
# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djcelery_email',
    'rest_framework',
    'login_details',
    'timer',
    'solution_groups',
    'roles_creation',
    'organisation_details',
    'knowledge_article',
    'category',
    'priority',
    'personal_details',
    'project_details',
    'resolution',
    'five_notifications',
    'history',
    'services',
    'celery',
    'django_celery_results',
    'cloudinary_storage',
    'cloudinary',
    'whatsapp_notifications',
    # ["whatsapp_notifications.apps.WhatsappNotificationsConfig"]
]

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'roles_creation.middlewares.RoleBasedAccessControlMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'Ticketing_tool.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, '../Frontend/build'),  # Add React build path here
        ],
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

WSGI_APPLICATION = 'Ticketing_tool.wsgi.application'

# Database configuration (PostgreSQL)
DATABASES = {
    'default': {   
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation settings
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Localization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Collect static files into STATIC_ROOT (for production use)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, '../Frontend/build/static'),  # Path to the React build directory
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Directory where static files will be collected

# Media files (for uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
AUTH_USER_MODEL = 'login_details.User'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
# EMAIL_HOST_USER = 'sridevigedela05@gmail.com'
# EMAIL_HOST_PASSWORD = 'ulgn jako ckts xodq'
EMAIL_HOST_USER = 'teerdavenigedela@gmail.com'
EMAIL_HOST_PASSWORD = 'vcig blpb lbdg sact'
# # Celery configuration
# CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Redis connection URL
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_ACCEPT_CONTENT = ['application/json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'Asia/Kolkata'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Redis connection URL (assuming Redis is running locally)
CELERY_RESULT_BACKEND = 'redis://192.168.1.12:6379/0'  # Where Celery stores results (Redis as well)
CELERY_ACCEPT_CONTENT = ['application/json']  # Celery task content serialization format
CELERY_TASK_SERIALIZER = 'json'  # Task serialization format
CELERY_RESULT_SERIALIZER = 'json'  # Result serialization format
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
  # Timezone for Celery tasks
#CELERY_RESULT_BACKEND = 'django-db'  # Use Django database as the result backend

# APPEND_SLASH=False
# broker_connection_retry_on_startup = 
# celery setting.
CELERY_CACHE_BACKEND = 'default'

# JWT settings for REST framework
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # ✅ correct
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
}

# Cloudinary settings



# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',
    }
}

# Security settings (for production)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
X_FRAME_OPTIONS = 'DENY'

# Ensure your SECRET_KEY is kept secret in production (don't hardcode it in settings.py)

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# SITE_URL = "http://192.168.1.12:8000/"
SITE_URL = "http://192.168.1.12:8000"

ASGI_APPLICATION = "Ticketing_tool.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",  # for development
    },
}


CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dngaxesdz',
    'API_KEY': '983585494285258',
    'API_SECRET': 'uYYsOTYP3tHUj_9Qa5Fn7KXH4_I',
    'SECURE': True,  
    'AUTHENTICATED': False
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'


WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID")
WA_ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN")
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN")
# WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN")
WA_API_VERSION = os.getenv("WA_API_VERSION", "v18.0")
