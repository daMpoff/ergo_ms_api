from django.apps import AppConfig

class VideoAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.video_analysis'
    label = 'video_analysis'
    verbose_name = 'Видео-анализ'
    
    # Конфигурация по умолчанию для GPU/CPU
    USE_GPU = False  # По умолчанию использовать CPU
    DEVICE = 'cpu'   # Устройство по умолчанию
    CUDA_VISIBLE_DEVICES = '0'  # Номер GPU устройства
    
    def ready(self):
        """Импортируем сигналы при запуске приложения"""
        import src.modules.video_analysis.signals