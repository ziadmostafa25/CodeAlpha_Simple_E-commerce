"""
Django settings for the Z-Store project.

Local development works with no configuration. For a real deployment set the
environment variables listed in README.md (at least DJANGO_SECRET_KEY,
DJANGO_DEBUG=0 and DJANGO_ALLOWED_HOSTS).
"""

import os
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name):
    return [item.strip() for item in os.environ.get(name, '').split(',') if item.strip()]


def env_decimal(name, default):
    value = os.environ.get(name, '').strip()
    return Decimal(value) if value else default


# Security -------------------------------------------------------------------
DEBUG = env_bool('DJANGO_DEBUG', True)
# Cloudinary credentials
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '').strip()
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

DEV_SECRET_KEY = 'django-insecure-local-development-key-do-not-use-in-production'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', DEV_SECRET_KEY)
if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured(
        'Set DJANGO_SECRET_KEY when DJANGO_DEBUG is off.'
    )

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '0'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    if env_bool('DJANGO_BEHIND_PROXY', False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition ----------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Z-Store apps
    'store',
    'cart',
    'orders',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zstore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'zstore.wsgi.application'


# Database ---------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=not DEBUG,
    )


# Authentication ------------------------------------------------------------------
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

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'store:home'
LOGOUT_REDIRECT_URL = 'store:home'


# Internationalization -------------------------------------------------------------
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Cairo'

USE_I18N = True

USE_TZ = True


# Static and media files ---------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Target of `python manage.py collectstatic` (needed for deployment only).
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Production storage ---------------------------------------------------------

if not DEBUG:
    if not all([
        CLOUDINARY_CLOUD_NAME,
        CLOUDINARY_API_KEY,
        CLOUDINARY_API_SECRET,
    ]):
        raise ImproperlyConfigured(
            'Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, '
            'and CLOUDINARY_API_SECRET in production.'
        )

    STORAGES = {
        'default': {
            'BACKEND': 'zstore.cloudinary_storage.CloudinaryMediaStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Store business rules (change them here or through environment variables) -------
# Delivery fee in EGP. 0 means delivery is free until you set a real value.
SHIPPING_FEE = env_decimal('ZSTORE_SHIPPING_FEE', Decimal('0'))
# Orders at or above this subtotal ship free. Leave unset to disable.
FREE_SHIPPING_THRESHOLD = env_decimal('ZSTORE_FREE_SHIPPING_THRESHOLD', None)
# Largest quantity of one item a customer can put in the cart.
CART_MAX_QUANTITY = 10

# Manual payment details. Leave empty until you have the real values: a method
# whose details are empty is shown as unavailable at checkout.
VODAFONE_CASH_NUMBER = os.environ.get('ZSTORE_VODAFONE_CASH_NUMBER', '').strip()
INSTAPAY_ADDRESS = os.environ.get('ZSTORE_INSTAPAY_ADDRESS', '').strip()



