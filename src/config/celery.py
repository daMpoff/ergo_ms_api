"""
Основной конфигурационный файл Celery для Django-приложения.
Отвечает за инициализацию Celery, настройку периодических задач и автоматическое обнаружение задач.

Функциональность:
    - Инициализация Celery приложения
    - Настройка интеграции с Django
    - Автоматическое обнаружение задач из установленных приложений
    - Конфигурация периодических задач (Celery Beat)
    
Периодические задачи:
    monitor-redis-status:
        - Задача: src.core.utils.tasks.monitor_redis_status
        - Интервал выполнения: каждые 10 секунд
        - Назначение: мониторинг состояния Redis сервера
"""

import os

from celery import Celery
from celery.schedules import timedelta

from django.conf import settings

from src.core.utils.auto_api.auto_config import get_env_deploy_type

# Определение типа развертывания и настройка переменной окружения Django
deploy_type = get_env_deploy_type()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', deploy_type)

# Инициализация Celery приложения
app = Celery('src')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Настройка пути к файлу состояния планировщика
app.conf.update(
    beat_schedule_filename="celery/celerybeat-schedule",
)

# Настройка периодических задач
app.conf.beat_schedule = {
    'monitor-redis-status': {
        'task': 'src.core.utils.tasks.monitor_redis_status',
        'schedule': timedelta(seconds=10),
    },
}