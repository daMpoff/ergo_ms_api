import os

from django.apps import AppConfig

from src.config.settings.static import PACKAGES_PATH, TRAINED_MODELS_PATH, MEDIA_ROOT

class VideoAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.video_analysis'
    label = 'video_analysis'
    verbose_name = 'Видео-анализ'
    
    # Конфигурация по умолчанию для GPU/CPU
    USE_GPU = True  # По умолчанию использовать CPU
    DEVICE = 'gpu'   # Устройство по умолчанию
    CUDA_VISIBLE_DEVICES = '0'  # Номер GPU устройства
    
    # Пути к моделям и ресурсам
    PACKAGES_PATH = PACKAGES_PATH
    SILERO_MODELS_PATH = os.path.join(PACKAGES_PATH, 'silero-models')
    TRAINED_MODELS_PATH = TRAINED_MODELS_PATH
    MEDIA_ROOT = MEDIA_ROOT
    
    # Пути к специфичным папкам модуля
    TTS_MODELS_DIR = os.path.join(TRAINED_MODELS_PATH, 'silero-tts')
    VOSK_MODELS_DIR = os.path.join(TRAINED_MODELS_PATH, 'vosk-model-ru-0.42')
    TRANSLATION_MODELS_DIR = os.path.join(TRAINED_MODELS_PATH, 'opus-mt-ru-fr')
    
    # Пути к медиа файлам модуля
    VIDEO_ANALYSIS_MEDIA = os.path.join(MEDIA_ROOT, 'video_analysis')
    INITIAL_VIDEO_DIR = os.path.join(VIDEO_ANALYSIS_MEDIA, 'initial_video')
    RESULTS_DIR = os.path.join(VIDEO_ANALYSIS_MEDIA, 'results')

    # Максимальное количество одновременных задач
    MAX_CONCURRENT_TASKS = 2
    
    def ready(self):
        """Импортируем сигналы при запуске приложения"""
        import src.modules.video_analysis.signals