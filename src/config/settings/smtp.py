from django.core.exceptions import ImproperlyConfigured

from src.config.env import env

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

try:
    EMAIL_HOST = env.str('EMAIL_HOST')
    EMAIL_PORT = env.str('EMAIL_PORT')
    EMAIL_USE_TLS = env.str('EMAIL_USE_TLS')

    EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
except (ImproperlyConfigured):
    pass