"""
Django settings for CareerConnect project.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(env_path):
    """Load simple KEY=VALUE pairs from a local .env file without overriding OS env vars."""
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _env_bool(name, default=False):
    """Parse boolean environment flags consistently."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name, default=()):
    """Parse comma-separated environment variable values into a cleaned list."""
    raw = os.environ.get(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(',') if item.strip()]


_load_dotenv(BASE_DIR / '.env')

DEBUG = _env_bool('DJANGO_DEBUG', default=True)

SECRET_KEY = (
    os.environ.get('DJANGO_SECRET_KEY', '').strip()
    or os.environ.get('SECRET_KEY', '').strip()
)
if not SECRET_KEY or SECRET_KEY == 'replace-with-a-long-random-50-plus-character-secret-key':
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY environment variable must be set (copy .env.example to .env and configure a secret key).'
    )

ALLOWED_HOSTS = _env_list(
    'DJANGO_ALLOWED_HOSTS',
    default=['127.0.0.1', 'localhost'] if DEBUG else [],
)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'jobs',
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

ROOT_URLCONF = 'CareerConnect.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'CareerConnect.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation

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


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static & Private Media Files

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Authentication, Sessions & Security Hardening

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SESSION_COOKIE_SECURE = _env_bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
    CSRF_COOKIE_SECURE = _env_bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
    SECURE_SSL_REDIRECT = _env_bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# Email Configuration

_email_host = os.environ.get('EMAIL_HOST', '').strip()
_email_backend = os.environ.get('DJANGO_EMAIL_BACKEND', '').strip()
if not _email_backend:
    _email_backend = (
        'django.core.mail.backends.smtp.EmailBackend'
        if (_email_host or not DEBUG)
        else 'django.core.mail.backends.console.EmailBackend'
    )

_default_mailer = {'BACKEND': _email_backend}
if _email_backend == 'django.core.mail.backends.smtp.EmailBackend':
    _default_mailer['OPTIONS'] = {
        'host': _email_host or 'localhost',
        'port': int(os.environ.get('EMAIL_PORT', '587')),
        'username': os.environ.get('EMAIL_HOST_USER', ''),
        'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
        'use_tls': _env_bool('EMAIL_USE_TLS', default=True),
        'use_ssl': _env_bool('EMAIL_USE_SSL', default=False),
    }

MAILERS = {
    'default': _default_mailer,
}
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@careerconnect.local')
