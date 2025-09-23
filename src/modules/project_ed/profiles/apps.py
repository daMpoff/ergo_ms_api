from django.apps import AppConfig

class ProjectEdProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.project_ed.profiles'
    label = 'project_ed_profiles'
    
    def ready(self):
        # Импортируем сигналы для их регистрации
        from . import signals