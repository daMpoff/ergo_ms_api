"""
Конфигурация Celery для модуля video_analysis.
Настройки задач анализа видео и их логирование.
"""

import logging
from typing import Dict, Any
from src.core.utils.celery.base import CeleryModuleConfig

# Получаем логгер для модуля
logger = logging.getLogger('video_analysis')


class VideoAnalysisCeleryConfig(CeleryModuleConfig):
    """
    Конфигурация Celery для модуля анализа видео.
    """
    
    def get_task_routes(self) -> Dict[str, str]:
        """Маршруты задач для анализа видео"""
        logger.debug("Настройка маршрутов задач для модуля video_analysis")
        return {
            'src.modules.video_analysis.tasks.*': {'queue': 'video_analysis'},
        }
    
    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        """Очереди задач для анализа видео"""
        logger.debug("Настройка очередей задач для модуля video_analysis")
        return {
            'video_analysis': {
                'exchange': 'video_analysis',
                'routing_key': 'video_analysis',
            }
        }
    
    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        """Аннотации задач для анализа видео"""
        logger.debug("Настройка аннотаций задач для модуля video_analysis")
        return {
            'src.modules.video_analysis.tasks.translate_video_analysis': {
                'time_limit': 7200,   # Таймаут 2 часа для команды перевода
                'soft_time_limit': 6900,  # Мягкий таймаут 1 час 55 минут
            },
        }
    
    def get_module_loggers(self) -> Dict[str, Any]:
        """Специализированные логгеры для модуля анализа видео"""
        loggers = super().get_module_loggers()
        
        # Добавляем специализированные логгеры
        loggers.update({
            'translation': self._get_logger('translation'),
        })
        
        return loggers
    
    def _get_logger(self, logger_name: str):
        """Создает специализированный логгер для модуля"""
        import logging
        return logging.getLogger(f'celery.module.{self.module_name}.{logger_name}')
    
    def get_additional_config(self) -> Dict[str, Any]:
        """Дополнительные настройки для модуля анализа видео"""
        return {
            # Специфичные настройки для анализа видео
            'video_analysis_max_concurrent_tasks': 4,  # Ограничиваем из-за ресурсов
            'video_analysis_memory_limit': '8GB',
            'video_analysis_gpu_enabled': True,
        } 