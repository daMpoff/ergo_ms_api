"""
Утилиты для логирования в модуле video_analysis
"""

import logging
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Получает логгер для модуля video_analysis
    
    Args:
        name: Дополнительное имя для логгера (например, 'tasks', 'models')
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    if name:
        return logging.getLogger(f'video_analysis.{name}')
    return logging.getLogger('video_analysis')


def log_task_start(task_name: str, **kwargs):
    """
    Логирует начало выполнения задачи
    
    Args:
        task_name: Название задачи
        **kwargs: Дополнительные параметры для логирования
    """
    logger = get_logger('tasks')
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"Начало выполнения задачи {task_name} с параметрами: {params}")


def log_task_complete(task_name: str, duration: float, **kwargs):
    """
    Логирует успешное завершение задачи
    
    Args:
        task_name: Название задачи
        duration: Время выполнения в секундах
        **kwargs: Дополнительные параметры для логирования
    """
    logger = get_logger('tasks')
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"Задача {task_name} успешно завершена за {duration:.2f} сек. Результат: {params}")


def log_task_error(task_name: str, error: Exception, **kwargs):
    """
    Логирует ошибку в задаче
    
    Args:
        task_name: Название задачи
        error: Объект исключения
        **kwargs: Дополнительные параметры для логирования
    """
    logger = get_logger('tasks')
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.error(f"Ошибка в задаче {task_name}: {str(error)}. Параметры: {params}")


def log_model_operation(operation: str, model_name: str, **kwargs):
    """
    Логирует операции с моделями БД
    
    Args:
        operation: Тип операции (create, update, delete, query)
        model_name: Название модели
        **kwargs: Дополнительные параметры для логирования
    """
    logger = get_logger('models')
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"Операция {operation} с моделью {model_name}. Параметры: {params}")


def log_file_operation(operation: str, file_path: str, **kwargs):
    """
    Логирует операции с файлами
    
    Args:
        operation: Тип операции (read, write, delete, move)
        file_path: Путь к файлу
        **kwargs: Дополнительные параметры для логирования
    """
    logger = get_logger('files')
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"Операция {operation} с файлом {file_path}. Параметры: {params}")


def log_performance_metric(metric_name: str, value: float, unit: str = "сек"):
    """
    Логирует метрики производительности
    
    Args:
        metric_name: Название метрики
        value: Значение метрики
        unit: Единица измерения
    """
    logger = get_logger('performance')
    logger.info(f"Метрика {metric_name}: {value:.3f} {unit}")
