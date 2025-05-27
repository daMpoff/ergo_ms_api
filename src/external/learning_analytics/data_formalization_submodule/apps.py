from django.apps import AppConfig

class ForecastingModuleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.learning_analytics.data_formalization_submodule'
    label = 'learning_analytics_data_formalization_submodule'