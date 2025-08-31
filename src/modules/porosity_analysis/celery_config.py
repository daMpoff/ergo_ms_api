"""
Конфигурация Celery для модуля porosity_analysis.
Настройки задач анализа пористости и их логирование.
"""

from typing import Dict, Any
from src.core.utils.celery.base import CeleryModuleConfig


class PorosityAnalysisCeleryConfig(CeleryModuleConfig):
    """
    Конфигурация Celery для модуля анализа пористости.
    """
    
    def get_task_routes(self) -> Dict[str, str]:
        """Маршруты задач для анализа пористости"""
        return {
            'src.modules.porosity_analysis.tasks.*': {'queue': 'porosity_analysis'},
        }
    
    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        """Очереди задач для анализа пористости"""
        return {
            'porosity_analysis': {
                'exchange': 'porosity_analysis',
                'routing_key': 'porosity_analysis',
            }
        }
    
    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        """Аннотации задач для анализа пористости"""
        return {
            'src.modules.porosity_analysis.tasks.run_porosity_analysis': {
                'time_limit': 3600,   # Таймаут 1 час
                'soft_time_limit': 3300,  # Мягкий таймаут 55 минут
            },
            'src.modules.porosity_analysis.tasks.cleanup_failed_analyses': {
                'time_limit': 600,   # Таймаут 10 минут
                'soft_time_limit': 540,  # Мягкий таймаут 9 минут
            },
            'src.modules.porosity_analysis.tasks.validate_analysis_files': {
                'time_limit': 300,   # Таймаут 5 минут
                'soft_time_limit': 240,  # Мягкий таймаут 4 минуты
            },
        }
    
    def get_module_loggers(self) -> Dict[str, Any]:
        """Специализированные логгеры для модуля анализа пористости"""
        loggers = super().get_module_loggers()
        
        # Добавляем специализированные логгеры
        loggers.update({
            'analysis': self._get_logger('analysis'),
            'cleanup': self._get_logger('cleanup'),
            'validation': self._get_logger('validation'),
        })
        
        return loggers
    
    def _get_logger(self, logger_name: str):
        """Создает специализированный логгер для модуля"""
        import logging
        return logging.getLogger(f'celery.module.{self.module_name}.{logger_name}')
    
    def get_additional_config(self) -> Dict[str, Any]:
        """Дополнительные настройки для модуля анализа пористости"""
        return {
            # Специфичные настройки для анализа пористости
            'porosity_analysis_max_concurrent_tasks': 2,
            'porosity_analysis_memory_limit': '2GB',
        } 