"""
Конфигурация Celery для модуля headhunter.
Настройки задач парсинга вакансий с HeadHunter.
"""

from typing import Dict, Any

from src.core.utils.celery.base import CeleryModuleConfig

class HeadhunterCeleryConfig(CeleryModuleConfig):
    """
    Конфигурация Celery для модуля парсинга HeadHunter.
    """
    
    def get_task_routes(self) -> Dict[str, str]:
        """Маршруты задач для парсинга HeadHunter"""
        return {
            'src.modules.vacancies_parser.headhunter.tasks.*': {'queue': 'headhunter'},
        }
    
    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        """Очереди задач для парсинга HeadHunter"""
        return {
            'headhunter': {
                'exchange': 'headhunter',
                'routing_key': 'headhunter',
            }
        }
    
    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        """Аннотации задач для парсинга HeadHunter"""
        return {
            'src.modules.vacancies_parser.headhunter.tasks.parse_hh_vacancies_task': {
                'time_limit': 7200,   # Таймаут 2 часа
                'soft_time_limit': 6900,  # Мягкий таймаут 1 час 55 минут
                'rate_limit': '100/h',   # Максимум 100 задач в час
            },
            'src.modules.vacancies_parser.headhunter.tasks.parse_single_vacancy_task': {
                'time_limit': 1800,   # Таймаут 30 минут
                'soft_time_limit': 1500,  # Мягкий таймаут 25 минут
                'rate_limit': '100/h',  # Максимум 100 задач в час
            },
        }
    
    def get_module_loggers(self) -> Dict[str, Any]:
        """Специализированные логгеры для модуля парсинга HeadHunter"""
        loggers = super().get_module_loggers()
        
        # Добавляем специализированные логгеры
        loggers.update({
            'parsing': self._get_logger('parsing'),
            'api': self._get_logger('api'),
        })
        
        return loggers
    
    def _get_logger(self, logger_name: str):
        """Создает специализированный логгер для модуля"""
        import logging
        return logging.getLogger(f'celery.module.{self.module_name}.{logger_name}')
    
    def get_additional_config(self) -> Dict[str, Any]:
        """Дополнительные настройки для модуля парсинга HeadHunter"""
        return {
            'headhunter_max_concurrent_tasks': 5,
            'headhunter_rate_limit': '10/m',  # 10 запросов в минуту
            'headhunter_retry_delay': 60,  # Задержка между повторами 60 секунд
        } 