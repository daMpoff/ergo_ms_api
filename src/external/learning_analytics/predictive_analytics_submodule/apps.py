from django.apps import AppConfig

class TrainingModuleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.learning_analytics.predictive_analytics_submodule'
    label = 'learning_analytics_predictive_analytics_submodule'