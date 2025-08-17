
import os
from dotenv import load_dotenv
from pathlib import Path
AUTH_USER_MODEL = 'maskan.User'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG') == 'False'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# CSRF trusted origins from env
_csrf_env = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(',') if o.strip()]


# SECRET_KEY = os.getenv('SECRET_KEY')
# DEBUG = os.getenv('DEBUG') == 'True'

# ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com', 'localhost', '127.0.0.1']


# Application definition

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
    
    

    # local
    'maskan',
    'one_to_one',
    'front',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # CSRF_COOKIE_SECURE = True  # HTTPS bo'lsa True
# CSRF_USE_SESSIONS = False  # Cookie orqali ishlatilsin
# ALLOWED_HOSTS = ['your-domain.com']  # Domeningizni kiriting
# CSRF_TRUSTED_ORIGINS = ['https://your-domain.com']
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bassic.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [],
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

WSGI_APPLICATION = 'bassic.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        # 'HOST': 'localhost', 
        # 'HOST': 'host.docker.internal',
        'PORT': os.getenv('DB_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
    # {
    #     'NAME': 'yourapp.validators.validate_password_length',
    # },
    # {
    #     'NAME': 'yourapp.validators.validate_password_not_numeric',
    # },
]



# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
# LANGUAGE_CODE = 'uz'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

CRISPY_TEMPLATE_PACK = "bootstrap4" 

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

STATICFILES_DIRS = [BASE_DIR / 'static']

STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CSRF_COOKIE_SECURE = True  # HTTPS bo'lsa True
# CSRF_USE_SESSIONS = False  # Cookie orqali ishlatilsin
# ALLOWED_HOSTS = ['your-domain.com']  # Domeningizni kiriting
# CSRF_TRUSTED_ORIGINS = ['https://your-domain.com']
