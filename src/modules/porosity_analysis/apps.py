from django.apps import AppConfig

class AnalysisPorosityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.porosity_analysis'
    label = 'porosity_analysis'
    # Количество потоков для подготовки отчетов при архивации (по умолчанию 8)
    report_zip_threads = 16
    # Количество потоков для загрузки файлов (по умолчанию 8)
    upload_threads = 16
    
    def ready(self):
        """Подключение сигналов при запуске приложения"""
        import src.modules.porosity_analysis.signals