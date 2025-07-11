from django.apps import AppConfig


class LMSConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.lms'
    label = 'lms'

    def ready(self):
        """Выполняется при инициализации приложения"""
        # Импортируем сигналы для их регистрации
        from . import signals
