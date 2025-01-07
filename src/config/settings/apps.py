from src.config.auto_config import discover_installed_apps

CORE_DIR = 'src/core'
EXTERNAL_MODULES_DIR = 'src/external_modules'

CORE_APPS = discover_installed_apps(CORE_DIR)
EXTERNAL_MODULES_APPS = discover_installed_apps(EXTERNAL_MODULES_DIR)

DEVELOPED_APPS = CORE_APPS + EXTERNAL_MODULES_APPS

INSTALLED_APPS = DEVELOPED_APPS + [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_yasg',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')