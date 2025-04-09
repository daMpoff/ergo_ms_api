from django.apps import AppConfig

class BiAnalysisDatawarehouseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.bi_analysis.datawarehouse'
    label = 'bi_analysis_datawarehouse'