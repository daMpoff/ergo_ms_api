"""
Конфигурация Celery для модуля impuls_analysis.
Настройки задач анализа импульса и их логирование.
"""

import logging
from typing import Dict, Any
from src.core.utils.celery.base import CeleryModuleConfig

# Получаем логгер для модуля
logger = logging.getLogger('impuls_analysis')


class ImpulsAnalysisCeleryConfig(CeleryModuleConfig):
    """
    Конфигурация Celery для модуля анализа импульса.
    """
    
    def get_task_routes(self) -> Dict[str, str]:
        """Маршруты задач для анализа импульса"""
        logger.debug("Настройка маршрутов задач для модуля impuls_analysis")
        return {
            'src.modules.impuls_analysis.tasks.*': {'queue': 'impuls_analysis'},
        }
    
    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        """Очереди задач для анализа импульса"""
        logger.debug("Настройка очередей задач для модуля impuls_analysis")
        return {
            'impuls_analysis': {
                'exchange': 'impuls_analysis',
                'routing_key': 'impuls_analysis',
            }
        }
    
    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        """Аннотации задач для анализа импульса"""
        logger.debug("Настройка аннотаций задач для модуля impuls_analysis")
        return {
            'src.modules.impuls_analysis.tasks.analyze_impuls_data': {
                'time_limit': 3600,   # Таймаут 1 час для анализа данных
                'soft_time_limit': 3300,  # Мягкий таймаут 55 минут
            },
            'src.modules.impuls_analysis.tasks.generate_protocol': {
                'time_limit': 1800,   # Таймаут 30 минут для генерации протокола
                'soft_time_limit': 1500,  # Мягкий таймаут 25 минут
            },
            'src.modules.impuls_analysis.tasks.process_excel_files': {
                'time_limit': 1200,   # Таймаут 20 минут для обработки Excel файлов
                'soft_time_limit': 900,   # Мягкий таймаут 15 минут
            },
        }
    
    def get_module_loggers(self) -> Dict[str, Any]:
        """Специализированные логгеры для модуля анализа импульса"""
        loggers = super().get_module_loggers()
        
        # Добавляем специализированные логгеры
        loggers.update({
            'excel_processing': self._get_logger('excel_processing'),
            'protocol_generation': self._get_logger('protocol_generation'),
            'data_analysis': self._get_logger('data_analysis'),
        })
        
        return loggers
    
    def _get_logger(self, logger_name: str):
        """Создает специализированный логгер для модуля"""
        import logging
        return logging.getLogger(f'celery.module.{self.module_name}.{logger_name}')
    
    def get_additional_config(self) -> Dict[str, Any]:
        """Дополнительные настройки для модуля анализа импульса"""
        return {
            # Специфичные настройки для анализа импульса
            'impuls_analysis_max_concurrent_tasks': 6,  # Больше задач для Excel обработки
            'impuls_analysis_memory_limit': '4GB',
            'impuls_analysis_excel_timeout': 300,  # 5 минут на обработку Excel файла
            'impuls_analysis_protocol_timeout': 600,  # 10 минут на генерацию протокола
        }
