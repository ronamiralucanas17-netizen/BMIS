import os
import glob
from pathlib import Path
from ctypes.util import find_library
from urllib.parse import parse_qsl, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-secret-key-for-bmis-development'

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis', # GeoDjango
    
    # Third-party apps
    'leaflet',
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'corsheaders',

    # Local apps
    'users.apps.UsersConfig',
    'residents.apps.ResidentsConfig',
    'gis_mapping.apps.GisMappingConfig',
    'analytics.apps.AnalyticsConfig',
    'barangay_services',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'users.middleware.AuditTrailMiddleware',
    'users.middleware.ProfileCompletionMiddleware', # Custom middleware
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

def _first_existing_path(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def _find_qgis_bin_dirs():
    roots = [r'C:\Program Files', r'C:\Program Files (x86)']
    bin_dirs = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            for name in os.listdir(root):
                if not name.startswith('QGIS '):
                    continue
                candidate = os.path.join(root, name, 'bin')
                if os.path.isdir(candidate):
                    bin_dirs.append(candidate)
        except OSError:
            continue
    return sorted(bin_dirs)


if os.name == 'nt':
    _qgis_bins = _find_qgis_bin_dirs()
    _qgis_bin = _qgis_bins[-1] if _qgis_bins else None

    _gdal_candidates = [os.environ.get('GDAL_LIBRARY_PATH')]
    _geos_candidates = [os.environ.get('GEOS_LIBRARY_PATH')]

    if _qgis_bin:
        _gdal_candidates.extend(sorted(glob.glob(os.path.join(_qgis_bin, 'gdal*.dll')), reverse=True))
        _geos_candidates.extend(sorted(glob.glob(os.path.join(_qgis_bin, 'geos_c*.dll')), reverse=True))

        os.environ['PATH'] = _qgis_bin + ';' + os.environ.get('PATH', '')
        qgis_root = os.path.dirname(_qgis_bin)
        gdal_data_dir = os.path.join(qgis_root, 'share', 'gdal')
        proj_lib_dir = os.path.join(qgis_root, 'share', 'proj')
        if os.path.exists(gdal_data_dir):
            os.environ.setdefault('GDAL_DATA', gdal_data_dir)
        if os.path.exists(proj_lib_dir):
            os.environ.setdefault('PROJ_LIB', proj_lib_dir)

    GDAL_LIBRARY_PATH = _first_existing_path(_gdal_candidates) or find_library('gdal')
    GEOS_LIBRARY_PATH = _first_existing_path(_geos_candidates) or find_library('geos_c')
else:
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH') or find_library('gdal')
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH') or find_library('geos_c')

    if GDAL_LIBRARY_PATH and not os.path.exists(GDAL_LIBRARY_PATH):
        import subprocess
        try:
            result = subprocess.run(
                ['find', '/nix/store', '-name', 'libgdal.so'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                GDAL_LIBRARY_PATH = result.stdout.strip().split('\n')[0]
        except Exception:
            pass

    if GEOS_LIBRARY_PATH and not os.path.exists(GEOS_LIBRARY_PATH):
        import subprocess
        try:
            result = subprocess.run(
                ['find', '/nix/store', '-name', 'libgeos_c.so'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                GEOS_LIBRARY_PATH = result.stdout.strip().split('\n')[0]
        except Exception:
            pass

def _database_from_url(url: str) -> dict:
    url = (url or '').strip()
    if url.startswith('postgis://'):
        url = 'postgresql://' + url[len('postgis://'):]

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    name = (parsed.path or '').lstrip('/')

    db = {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': name,
        'USER': parsed.username or '',
        'PASSWORD': parsed.password or '',
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port) if parsed.port else '',
        'DISABLE_SERVER_SIDE_CURSORS': True,
        'GDAL_LIBRARY_PATH': GDAL_LIBRARY_PATH,
        'GEOS_LIBRARY_PATH': GEOS_LIBRARY_PATH,
    }

    if 'sslmode' in query:
        db['OPTIONS'] = {'sslmode': query['sslmode']}

    return db


DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': _database_from_url(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'bmis_db',
            'USER': 'postgres',
            'PASSWORD': 'root',
            'HOST': 'localhost',
            'PORT': '5432',
            'DISABLE_SERVER_SIDE_CURSORS': True,
            'GDAL_LIBRARY_PATH': GDAL_LIBRARY_PATH,
            'GEOS_LIBRARY_PATH': GEOS_LIBRARY_PATH,
        }
    }

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Leaflet settings
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (11.0044, 124.6075), # Ormoc City Coordinates
    'DEFAULT_ZOOM': 13,
    'MAX_ZOOM': 18,
    'MIN_ZOOM': 10,
}

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'users:login'
LOGIN_URL = 'users:login'

# Email settings for forgot password
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # For development

# GDAL & GEOS Configuration for Windows (GeoDjango)
if os.name == 'nt':
    OSGEO4W_ROOT = r'C:\Users\rona2\AppData\Local\Programs\OSGeo4W'
    if os.path.exists(OSGEO4W_ROOT):
        os.environ['PATH'] = OSGEO4W_ROOT + r'\bin;' + os.environ['PATH']
        gdal_data_dir = os.path.join(OSGEO4W_ROOT, 'share', 'gdal')
        proj_lib_dir = os.path.join(OSGEO4W_ROOT, 'share', 'proj')
        if os.path.exists(gdal_data_dir):
            os.environ['GDAL_DATA'] = gdal_data_dir
        if os.path.exists(proj_lib_dir):
            os.environ['PROJ_LIB'] = proj_lib_dir
