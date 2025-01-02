import os

from src.config.settings.base import (
    BASE_DIR
)

STATIC_URL = '/static/'
STATIC_ROOT = 'static'

MEDIA_URL = '/media/'
MEDIA_ROOT = 'media'

LOGS_URL = '/logs/'
LOGS_ROOT = os.path.join(BASE_DIR.parent, 'logs')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'