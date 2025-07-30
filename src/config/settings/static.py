"""
Файл содержащий конфигурацию статических и медиа файлов, а также логов для Django-приложения.
Он включает настройки URL и корневых директорий для статических файлов, медиа файлов и логов.
"""

import os

from src.config.settings.base import API_DIR

# URL для доступа к статическим файлам.
STATIC_URL = '/static/'

# Корневая директория для статических файлов.
STATIC_ROOT = 'static'

# URL для доступа к медиа файлам.
MEDIA_URL = '/media/'

# Корневая директория для медиа файлов.
MEDIA_ROOT = 'media'

# URL для доступа к логам.
LOGS_URL = '/logs/'

# Корневая директория для логов.
LOGS_ROOT = os.path.join(API_DIR, 'logs')

# Хранилище для статических файлов, использующее Whitenoise для сжатия и кэширования.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Корневая директория для ресурсов.
RESOURCES_DIR = os.path.join(API_DIR, 'resources')

# Корневая директория для обученных моделей.
TRAINED_MODELS_PATH = os.path.join(API_DIR, 'trained_models')

# Корневая директория для сторонних программ.
PACKAGES_PATH = os.path.join(API_DIR, 'packages')