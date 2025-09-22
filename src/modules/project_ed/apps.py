from django.apps import AppConfig


class ProjectEdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.project_ed'
    label = 'project_ed'

    def ready(self):
        """Выполняется при инициализации приложения"""
        # Импортируем сигналы для их регистрации
        from . import signals