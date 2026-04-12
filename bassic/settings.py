import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Maxfiy kalit va DEBUG sozlamalari
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Domenlar va hostlar
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '').split(',') if host.strip()]

# Lokal dev uchun umumiy hostlarni qo'shib qo'yamiz
if DEBUG:
    for _host in ('localhost', '127.0.0.1', '0.0.0.0'):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)

# CSRF uchun ishonchli domenlar/protokollar
_csrf_env = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []

# HTTPS ishlatilsa CSRF cookie faqat HTTPS orqali yuborilsin
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'

# CSRF tokenini sessiya orqali ishlatish (default: False, cookie ishlatiladi)
CSRF_USE_SESSIONS = os.getenv('CSRF_USE_SESSIONS', 'False') == 'True'

# Maxsus foydalanuvchi modeli
AUTH_USER_MODEL = 'maskan.User'

# Ilovalar
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'bootstrap4',
    # local apps
    'maskan',
    'one_to_one',
    'front',
    # grave-care admin apps
    'apps.core',
    'apps.catalog',
    'apps.orders',
    # telegram bot language/user management
    'apps.botapp',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF himoyasi
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL konfiguratsiyasi
ROOT_URLCONF = 'bassic.urls'

# Template sozlamalari
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

# WSGI
WSGI_APPLICATION = 'bassic.wsgi.application'

# Database
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
if DB_HOST == 'jazzmin-db' and not os.path.exists('/.dockerenv'):
    # "jazzmin-db" is the Docker service name; use localhost when running directly.
    DB_HOST = '127.0.0.1'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': DB_HOST,
        'PORT': os.getenv('DB_PORT'),
    }
}

# Parol validatorlari
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Xalqaro sozlamalar
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Crispy forms
CRISPY_TEMPLATE_PACK = "bootstrap4" 

# Static fayllar
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Telegram bot (grave-care services)
TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN', '')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID', '')

# Bot admin IDs (comma-separated in .env)
ADMIN_IDS = os.getenv('ADMIN_IDS', TELEGRAM_ADMIN_CHAT_ID)

# Google Sheets integration
GOOGLE_SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID', '')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', '')

# Jazzmin Admin Theme Settings
JAZZMIN_SETTINGS = {
    "site_title": "Grave Care Admin",
    "site_header": "Grave Care",
    "site_brand": "Grave Care",
    "welcome_sign": "Xush kelibsiz!",
    "copyright": "Grave Care Services",

    # Custom links in top menu
    "topmenu_links": [
        {"name": "Bosh sahifa", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Bot Analitika", "url": "/admin/analytics/", "permissions": ["auth.view_user"]},
        {"name": "Buyurtmalar", "url": "/admin/order-analytics/", "permissions": ["auth.view_user"]},
    ],

    # Custom icons
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "botapp.TelegramUser": "fas fa-robot",
        "botapp.CatalogService": "fas fa-broom",
        "botapp.CatalogFlowerCategory": "fas fa-folder",
        "botapp.CatalogFlowerProduct": "fas fa-seedling",
        "catalog.Service": "fas fa-broom",
        "catalog.Flower": "fas fa-seedling",
        "catalog.Region": "fas fa-map",
        "catalog.District": "fas fa-map-marker",
        "catalog.Cemetery": "fas fa-church",
        "orders.Order": "fas fa-shopping-cart",
    },

    # Custom links to appear in the side menu
    "custom_links": {
        "botapp": [
            {
                "name": "Bot Analitika",
                "url": "/admin/analytics/",
                "icon": "fas fa-chart-line",
                "permissions": ["auth.view_user"]
            },
            {
                "name": "Buyurtmalar Analitika",
                "url": "/admin/order-analytics/",
                "icon": "fas fa-shopping-cart",
                "permissions": ["auth.view_user"]
            },
        ],
    },

    "show_ui_builder": False,
}
