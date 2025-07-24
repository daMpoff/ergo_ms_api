from django.apps import AppConfig

class VideoAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.video_analysis'
    label = 'video_analysis'
    verbose_name = 'Видео-анализ'
    
    def ready(self):
        """Импортируем сигналы при запуске приложения"""
        import src.modules.video_analysis.signals