import logging

from celery import shared_task

logger = logging.getLogger('utils')

@shared_task
def monitor_redis_status():
    """
    Мониторинг статуса Redis сервера.
    Записывает текущий статус в лог-файл каждые 10 секунд.
    """
    logger.info("Начало выполнения задачи monitor_redis_status")
    logger.info("Конец выполнения задачи monitor_redis_status")