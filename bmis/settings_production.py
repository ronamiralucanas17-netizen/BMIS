"""
Production settings for BMIS deployment.
Copy this file to settings.py on your production server,
or use environment variables for configuration.
"""

import os
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production')

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH')
GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH')

def _check_gdal_available():
    if os.name == 'nt':
        if GDAL_LIBRARY_PATH and os.path.exists(GDAL_LIBRARY_PATH):
            return True
        default_path = r'C:\Users\rona2\AppData\Local\Programs\OSGeo4W\bin\gdal312.dll'
        if os.path.exists(default_path):
            return True
        return False
    else:
        if GDAL_LIBRARY_PATH and os.path.exists(GDAL_LIBRARY_PATH):
            return True
        from ctypes.util import find_library
        gdal_path = find_library('gdal')
        if gdal_path:
            return True
        for path in [
            '/usr/lib/libgdal.so',
            '/usr/local/lib/libgdal.so',
            '/usr/lib/x86_64-linux-gnu/libgdal.so',
            '/usr/lib/libgdal.so.3',
            '/usr/lib/x86_64-linux-gnu/libgdal.so.3',
        ]:
            if os.path.exists(path):
                return True
        return False

GIS_AVAILABLE = _check_gdal_available()

_base_apps = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

_third_party_apps = [
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'corsheaders',
]

if GIS_AVAILABLE:
    _third_party_apps.append('leaflet')

_local_apps = [
    'users.apps.UsersConfig',
    'residents.apps.ResidentsConfig',
    'analytics.apps.AnalyticsConfig',
    'barangay_services',
]

if GIS_AVAILABLE:
    _base_apps.append('django.contrib.gis')
    _local_apps.append('gis_mapping.apps.GisMappingConfig')

INSTALLED_APPS = _base_apps + _third_party_apps + _local_apps

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'users.middleware.AuditTrailMiddleware',
    'users.middleware.ProfileCompletionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bmis.urls'

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

WSGI_APPLICATION = 'bmis.wsgi.application'

def _database_from_url(url: str) -> dict:
    url = (url or '').strip()
    if url.startswith('postgis://'):
        url = 'postgresql://' + url[len('postgis://'):]

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    name = (parsed.path or '').lstrip('/')

    engine = 'django.contrib.gis.db.backends.postgis' if GIS_AVAILABLE else 'django.db.backends.postgresql'
    db = {
        'ENGINE': engine,
        'NAME': name,
        'USER': parsed.username or '',
        'PASSWORD': parsed.password or '',
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port) if parsed.port else '',
    }

    if GIS_AVAILABLE:
        db['DISABLE_SERVER_SIDE_CURSORS'] = True
        db['GDAL_LIBRARY_PATH'] = GDAL_LIBRARY_PATH
        db['GEOS_LIBRARY_PATH'] = GEOS_LIBRARY_PATH

    if 'sslmode' in query:
        db['OPTIONS'] = {'sslmode': query['sslmode']}

    return db


DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': _database_from_url(DATABASE_URL)}
else:
    engine = 'django.contrib.gis.db.backends.postgis' if GIS_AVAILABLE else 'django.db.backends.postgresql'
    DATABASES = {
        'default': {
            'ENGINE': engine,
            'NAME': os.environ.get('DB_NAME', 'bmis_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
    if GIS_AVAILABLE:
        DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
        DATABASES['default']['GDAL_LIBRARY_PATH'] = GDAL_LIBRARY_PATH
        DATABASES['default']['GEOS_LIBRARY_PATH'] = GEOS_LIBRARY_PATH

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

if GIS_AVAILABLE:
    LEAFLET_CONFIG = {
        'DEFAULT_CENTER': (11.0044, 124.6075),
        'DEFAULT_ZOOM': 13,
        'MAX_ZOOM': 18,
        'MIN_ZOOM': 10,
    }

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'users:login'
LOGIN_URL = 'users:login'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
