"""
Конфигурационный файл для модуля анализа пористости.
Содержит настройки для ограничения количества одновременных анализов и другие параметры.
"""

import os
from django.conf import settings

# Настройки для ограничения количества одновременных анализов
MAX_CONCURRENT_ANALYSES = getattr(settings, 'POROSITY_MAX_CONCURRENT_ANALYSES', 3)
ANALYSIS_TIMEOUT_SECONDS = getattr(settings, 'POROSITY_ANALYSIS_TIMEOUT', 1800)  # 30 минут
ANALYSIS_RETRY_DELAY_SECONDS = getattr(settings, 'POROSITY_RETRY_DELAY', 60)

# Настройки очереди
POROSITY_QUEUE_NAME = 'porosity_analysis'
POROSITY_QUEUE_CONCURRENCY = getattr(settings, 'POROSITY_QUEUE_CONCURRENCY', 2)

# Настройки файловой системы
MEDIA_ROOT = getattr(settings, 'MEDIA_ROOT', 'media')
POROSITY_UPLOAD_DIR = os.path.join(MEDIA_ROOT, 'porosity_analysis', 'initial_photo')
POROSITY_RESULTS_DIR = os.path.join(MEDIA_ROOT, 'porosity_analysis', 'results')

# Настройки очистки
CLEANUP_FAILED_ANALYSES_DAYS = getattr(settings, 'POROSITY_CLEANUP_DAYS', 7)
VALIDATE_FILES_INTERVAL_HOURS = getattr(settings, 'POROSITY_VALIDATE_INTERVAL', 24)

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
    def get_queue_name(cls):
        """Возвращает имя очереди для анализа пористости"""
        return POROSITY_QUEUE_NAME
    
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