"""
Конфигурация Celery для модуля geoanalyzer.
Настройки задач геоанализа городов.
"""

from typing import Dict, Any
from src.core.utils.celery.base import CeleryModuleConfig


class GeoanalyzerCeleryConfig(CeleryModuleConfig):
    """
    Конфигурация Celery для модуля геоанализа городов.
    """
    
    def get_task_routes(self) -> Dict[str, str]:
        """Маршруты задач для модуля геоанализа"""
        return {
            'src.modules.cities_expansion.geoanalyzer.tasks.*': {'queue': 'geoanalyzer'},
        }
    
    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        """Очереди задач для модуля геоанализа"""
        return {
            'geoanalyzer': {
                'exchange': 'geoanalyzer',
                'routing_key': 'geoanalyzer',
            }
        }
    
    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        """Аннотации задач для модуля геоанализа"""
        return {
            'src.modules.cities_expansion.geoanalyzer.tasks.process_map_group': {
                'time_limit': 3600,      # Таймаут 1 час
                'soft_time_limit': 3300,  # Мягкий таймаут 55 минут
                'rate_limit': '2/h',      # Максимум 2 задачи в час
            },
        }
    
    def get_module_loggers(self) -> Dict[str, Any]:
        """Специализированные логгеры для модуля геоанализа"""
        loggers = super().get_module_loggers()
        
        # Добавляем специализированные логгеры
        loggers.update({
            'processing': self._get_logger('processing'),
            'analysis': self._get_logger('analysis'),
            'maps': self._get_logger('maps'),
        })
        
        return loggers
    
    def _get_logger(self, logger_name: str):
        """Создает специализированный логгер для модуля"""
        import logging
        return logging.getLogger(f'celery.module.{self.module_name}.{logger_name}')
    
    def get_additional_config(self) -> Dict[str, Any]:
        """Дополнительные настройки для модуля геоанализа"""
        return {
            'geoanalyzer_max_concurrent_tasks': 1,  # Только одна задача одновременно
            'geoanalyzer_batch_size': 1,            # Обработка по одной карте
            'geoanalyzer_memory_limit': '2GB',      # Лимит памяти для обработки карт
        } 