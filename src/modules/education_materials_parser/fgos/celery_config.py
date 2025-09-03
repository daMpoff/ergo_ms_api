"""
Конфигурация Celery для модуля fgos.
Настройки задач парсинга ФГОС и их логирование.
"""

from typing import Dict, Any
from src.core.utils.celery.base import CeleryModuleConfig


class FgosCeleryConfig(CeleryModuleConfig):
    """
    Конфигурация Celery для модуля парсинга ФГОС.
    """
    
    def get_task_routes(self) -> Dict[str, str]:
        """Маршруты задач для парсинга ФГОС"""
        return {
            'src.modules.education_materials_parser.fgos.tasks.*': {'queue': 'fgos'},
        }
    
    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        """Очереди задач для парсинга ФГОС"""
        return {
            'fgos': {
                'exchange': 'fgos',
                'routing_key': 'fgos',
            }
        }
    
    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        """Аннотации задач для парсинга ФГОС"""
        return {
            'src.modules.education_materials_parser.fgos.tasks.parse_all_fgos_documents': {
                'time_limit': 7200,   # Таймаут 2 часа
                'soft_time_limit': 6900,  # Мягкий таймаут 1 час 55 минут
            },
            'src.modules.education_materials_parser.fgos.tasks.download_missing_fgos_files': {
                'time_limit': 3600,   # Таймаут 1 час
                'soft_time_limit': 3300,  # Мягкий таймаут 55 минут
            },
            'src.modules.education_materials_parser.fgos.tasks.update_existing_fgos_documents': {
                'time_limit': 1800,   # Таймаут 30 минут
                'soft_time_limit': 1500,  # Мягкий таймаут 25 минут
            },
            'src.modules.education_materials_parser.fgos.tasks.cleanup_orphaned_fgos_files': {
                'time_limit': 600,   # Таймаут 10 минут
                'soft_time_limit': 540,  # Мягкий таймаут 9 минут
            },
        }
    
    def get_module_loggers(self) -> Dict[str, Any]:
        """Специализированные логгеры для модуля парсинга ФГОС"""
        loggers = super().get_module_loggers()
        
        # Добавляем специализированные логгеры
        loggers.update({
            'parsing': self._get_logger('parsing'),
            'downloading': self._get_logger('downloading'),
            'updating': self._get_logger('updating'),
            'cleanup': self._get_logger('cleanup'),
        })
        
        return loggers
    
    def _get_logger(self, logger_name: str):
        """Создает специализированный логгер для модуля"""
        import logging
        return logging.getLogger(f'celery.module.{self.module_name}.{logger_name}')
    
    def get_additional_config(self) -> Dict[str, Any]:
        """Дополнительные настройки для модуля парсинга ФГОС"""
        return {
            # Специфичные настройки для парсинга ФГОС
            'fgos_max_concurrent_tasks': 2,
            'fgos_download_delay': 1.0,  # Задержка между скачиваниями в секундах
            'fgos_max_retries': 3,
        } 