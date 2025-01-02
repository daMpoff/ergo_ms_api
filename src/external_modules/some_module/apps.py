from django.apps import AppConfig

class Some_moduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external_modules.some_module'