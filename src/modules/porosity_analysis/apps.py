from django.apps import AppConfig

class AnalysisPorosityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.porosity_analysis'
    label = 'porosity_analysis'
    
    def ready(self):
        """Подключение сигналов при запуске приложения"""
        import src.modules.porosity_analysis.signals