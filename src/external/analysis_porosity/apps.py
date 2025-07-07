from django.apps import AppConfig

class AnalysisPorosityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.analysis_porosity'
    verbose_name = 'Анализ пористости'
    label = 'analysis_porosity'
    
    def ready(self):
        """Подключение сигналов при запуске приложения"""
        import src.external.analysis_porosity.signals