from django.apps import AppConfig

class BiAnalysisDbConnectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.bi_analysis.db_connect'
    label = 'bi_analysis_db_connect'