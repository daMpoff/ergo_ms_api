from django.apps import AppConfig

class ExpertSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.expert_system'
    label = 'expert_system'