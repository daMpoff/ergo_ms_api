from django.apps import AppConfig


class LMSConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.lms'
    verbose_name = 'Learning Management System'
