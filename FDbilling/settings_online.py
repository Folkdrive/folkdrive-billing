"""
ONLINE settings for PythonAnywhere
"""
import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security - different for online
SECRET_KEY = 'django-insecure-folkdrive-pythonanywhere-2025-secret-key-make-this-very-long-and-random-123456789'
DEBUG = False  # False for production
ALLOWED_HOSTS = ['Folkdrive.pythonanywhere.com']  # ✅ CORRECT

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes", 
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "FD",
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", 
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "FDbilling.urls"
WSGI_APPLICATION = "FDbilling.wsgi.application"

# Database - MySQL for PythonAnywhere (CORRECTED FORMAT)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'Folkdrive$folkdrive',  # ⚠️ CORRECTED: PythonAnywhere adds $username
        'USER': 'Folkdrive',            # ✅ CORRECT
        'PASSWORD': 'Folkdrive@12',     # ✅ CORRECT (but keep this safe!)
        'HOST': 'Folkdrive.mysql.pythonanywhere-services.com',  # ✅ CORRECT
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = "/home/Folkdrive/folkdrive-billing/staticfiles"  # ⚠️ Check folder name

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Company settings
COMPANY_LOGO_URL = '/static/images/logo.png'
WO_NUMBER_PREFIX = 'FDWO'
INVOICE_NUMBER_PREFIX = 'INV'

# Whitenoise for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True