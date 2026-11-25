# -*- coding: utf-8 -*-
"""
settings.py - Configuracion del Sistema de Gestion de Produccion
Manufacturera de Calzado 3-JJJ-A

Django 4.2 compatible - Windows 7
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# CONFIGURACIONES BASICAS
# ============================================================
SECRET_KEY = 'django-insecure-tu-clave-secreta-aqui-cambiar-en-produccion'

DEBUG = True

ALLOWED_HOSTS = ['*']


# ============================================================
# APLICACIONES INSTALADAS
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # TU APP PRINCIPAL
    'core',
]


# ============================================================
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Middlewares personalizados
    'core.middleware.SesionActivaMiddleware',
    'core.middleware.SeguridadEntradaMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
]


# ============================================================
# URLS
# ============================================================
ROOT_URLCONF = 'tu_proyecto.urls'


# ============================================================
# TEMPLATES
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
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


# ============================================================
# WSGI
# ============================================================
WSGI_APPLICATION = 'tu_proyecto.wsgi.application'


# ============================================================
# BASE DE DATOS (SQLite por defecto)
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ============================================================
# VALIDACION DE CONTRASEÑAS
# ============================================================
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


# ============================================================
# INTERNACIONALIZACION
# ============================================================
LANGUAGE_CODE = 'es-419'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True


# ============================================================
# ARCHIVOS ESTATICOS (STATIC FILES)
# ============================================================
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'core' / 'static',   # ← Bootstrap Icons offline
]

# En produccion (collectstatic)
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ============================================================
# ARCHIVOS DE MEDIA (imagenes de modelos)
# ============================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ============================================================
# CONFIGURACION DE SESION (seguridad)
# ============================================================
SESSION_COOKIE_AGE = 1800  # 30 minutos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = '3jjja_sessionid'


# ============================================================
# CSRF PROTECTION
# ============================================================
CSRF_COOKIE_HTTPONLY = True


# ============================================================
# REDIRECCIONES DE LOGIN/LOGOUT
# ============================================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'


# ============================================================
# CONFIGURACION DE MENSAJES
# ============================================================
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'info',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}


# ============================================================
# HANDLER PARA ERRORES 403
# ============================================================
HANDLER403 = 'core.views.error_403_view'


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
