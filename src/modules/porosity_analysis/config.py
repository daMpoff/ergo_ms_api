"""
Конфигурационный файл для модуля анализа пористости.
Содержит настройки для ограничения количества одновременных анализов и другие параметры.
"""

import os
from django.conf import settings

# Настройки для модуля анализа пористости
MAX_CONCURRENT_ANALYSES = 5  # Максимальное количество одновременных анализов
ANALYSIS_TIMEOUT_SECONDS = 1800  # Таймаут анализа в секундах (30 минут)
ANALYSIS_RETRY_DELAY_SECONDS = 60  # Задержка между повторными попытками в секундах
POROSITY_QUEUE_CONCURRENCY = 5  # Количество воркеров для очереди анализа пористости
CLEANUP_FAILED_ANALYSES_DAYS = 7  # Количество дней для очистки неудачных анализов
VALIDATE_FILES_INTERVAL_HOURS = 24  # Интервал проверки файлов в часах

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