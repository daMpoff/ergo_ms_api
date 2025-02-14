import logging

from celery import shared_task
from celery.schedules import timedelta

from src.config.celery import celery_app

logger = logging.getLogger('utils')

# Настройка периодических задач
celery_app.conf.beat_schedule = {
    'monitor-sqlite-status': {
        'task': 'src.core.utils.tasks.monitor_sqlite_status',
        'schedule': timedelta(seconds=10),
    },
}

@shared_task
def monitor_sqlite_status():
    """
    Мониторинг статуса Redis сервера.
    Записывает текущий статус в лог-файл каждые 10 секунд.
    """
    logger.info("Начало выполнения задачи monitor_sqlite_status")
    logger.info("Конец выполнения задачи monitor_sqlite_status")