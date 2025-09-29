"""
Конфигурационный файл для модуля анализа пористости.
Содержит настройки для ограничения количества одновременных анализов и другие параметры.
"""

import os
from django.conf import settings
from django.apps import apps

# Настройки для модуля анализа пористости
MAX_CONCURRENT_ANALYSES = 6  # Максимальное количество одновременных анализов
ANALYSIS_TIMEOUT_SECONDS = 1800  # Таймаут анализа в секундах (30 минут)
ANALYSIS_RETRY_DELAY_SECONDS = 60  # Задержка между повторными попытками в секундах
POROSITY_QUEUE_CONCURRENCY = 5  # Количество воркеров для очереди анализа пористости
CLEANUP_FAILED_ANALYSES_DAYS = 7  # Количество дней для очистки неудачных анализов
VALIDATE_FILES_INTERVAL_HOURS = 24  # Интервал проверки файлов в часах
DEFAULT_REPORT_ZIP_THREADS = 8  # Количество потоков для подготовки отчетов в ZIP по умолчанию
DEFAULT_UPLOAD_THREADS = 8  # Количество потоков для загрузки файлов по умолчанию
DEFAULT_ARCHIVE_CHUNK_SIZE = 50  # Размер чанка для создания частичных архивов
DEFAULT_ARCHIVE_MERGE_THREADS = 4  # Количество потоков для объединения архивов
DEFAULT_FILE_CACHE_SIZE = 1000  # Размер кэша для файлов отчетов

# Настройки файловой системы
MEDIA_ROOT = getattr(settings, 'MEDIA_ROOT', 'media')
POROSITY_UPLOAD_DIR = os.path.join(MEDIA_ROOT, 'porosity_analysis', 'initial_photo')
POROSITY_RESULTS_DIR = os.path.join(MEDIA_ROOT, 'porosity_analysis', 'results')

class PorosityAnalysisConfig:
    """Класс для управления конфигурацией анализа пористости"""
    
    @classmethod
    def get_max_concurrent_analyses(cls):
        """Возвращает максимальное количество одновременных анализов"""
        return MAX_CONCURRENT_ANALYSES
    
    @classmethod
    def get_analysis_timeout(cls):
        """Возвращает таймаут для анализа в секундах"""
        return ANALYSIS_TIMEOUT_SECONDS
    
    @classmethod
    def get_retry_delay(cls):
        """Возвращает задержку между повторными попытками в секундах"""
        return ANALYSIS_RETRY_DELAY_SECONDS
    
    @classmethod
    def get_queue_concurrency(cls):
        """Возвращает количество воркеров для очереди анализа пористости"""
        return POROSITY_QUEUE_CONCURRENCY
    
    @classmethod
    def get_upload_directory(cls):
        """Возвращает директорию для загрузки изображений"""
        return POROSITY_UPLOAD_DIR
    
    @classmethod
    def get_results_directory(cls):
        """Возвращает директорию для результатов анализа"""
        return POROSITY_RESULTS_DIR
    
    @classmethod
    def get_cleanup_days(cls):
        """Возвращает количество дней для очистки неудачных анализов"""
        return CLEANUP_FAILED_ANALYSES_DAYS
    
    @classmethod
    def get_validate_interval_hours(cls):
        """Возвращает интервал проверки файлов в часах"""
        return VALIDATE_FILES_INTERVAL_HOURS 

    @classmethod
    def get_report_zip_threads(cls) -> int:
        """Возвращает количество потоков для подготовки отчетов при архивации.

        Значение читается из AppConfig `AnalysisPorosityConfig.report_zip_threads`,
        если доступно, иначе используется DEFAULT_REPORT_ZIP_THREADS.
        """
        try:
            app_config = apps.get_app_config('porosity_analysis')
            value = getattr(app_config, 'report_zip_threads', None)
            if isinstance(value, int) and value > 0:
                return value
        except Exception:
            pass
        return DEFAULT_REPORT_ZIP_THREADS

    @classmethod
    def get_upload_threads(cls) -> int:
        """Возвращает количество потоков для загрузки файлов.

        Значение читается из AppConfig `AnalysisPorosityConfig.upload_threads`,
        если доступно, иначе используется DEFAULT_UPLOAD_THREADS.
        """
        try:
            app_config = apps.get_app_config('porosity_analysis')
            value = getattr(app_config, 'upload_threads', None)
            if isinstance(value, int) and value > 0:
                return value
        except Exception:
            pass
        return DEFAULT_UPLOAD_THREADS

    @classmethod
    def get_archive_chunk_size(cls) -> int:
        """Возвращает размер чанка для создания частичных архивов."""
        try:
            app_config = apps.get_app_config('porosity_analysis')
            value = getattr(app_config, 'archive_chunk_size', None)
            if isinstance(value, int) and value > 0:
                return value
        except Exception:
            pass
        return DEFAULT_ARCHIVE_CHUNK_SIZE

    @classmethod
    def get_archive_merge_threads(cls) -> int:
        """Возвращает количество потоков для объединения архивов."""
        try:
            app_config = apps.get_app_config('porosity_analysis')
            value = getattr(app_config, 'archive_merge_threads', None)
            if isinstance(value, int) and value > 0:
                return value
        except Exception:
            pass
        return DEFAULT_ARCHIVE_MERGE_THREADS

    @classmethod
    def get_file_cache_size(cls) -> int:
        """Возвращает размер кэша для файлов отчетов."""
        try:
            app_config = apps.get_app_config('porosity_analysis')
            value = getattr(app_config, 'file_cache_size', None)
            if isinstance(value, int) and value > 0:
                return value
        except Exception:
            pass
        return DEFAULT_FILE_CACHE_SIZE