"""
Основной конфигурационный файл Celery для Django-приложения.
Отвечает за инициализацию Celery, настройку периодических задач и автоматическое обнаружение задач.

Функциональность:
    - Инициализация Celery приложения
    - Настройка интеграции с Django
    - Автоматическое обнаружение задач из установленных приложений
"""

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

from src.core.utils.auto_api.auto_config import get_env_deploy_type

# Определение типа развертывания и настройка переменной окружения Django
deploy_type = get_env_deploy_type()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', deploy_type)

# Инициализация Celery приложения
celery_app = Celery('src')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Настройка пути к файлу состояния планировщика и периодических задач
celery_app.conf.update(
    beat_schedule_filename="celery/celerybeat-schedule",
    broker_url='sqla+sqlite:///celerydb.sqlite',
    result_backend='db+sqlite:///results.sqlite',
    task_routes={
        'external.analysis_porosity.tasks.*': {'queue': 'porosity_analysis'},
    },
    task_default_queue='default',
    task_queues={
        'default': {},
        'porosity_analysis': {
            'exchange': 'porosity_analysis',
            'routing_key': 'porosity_analysis',
        },
    },
    # Настройки для ограничения количества одновременных задач
    task_annotations={
        'external.analysis_porosity.tasks.run_porosity_analysis': {
            'rate_limit': '5/m',  # Максимум 5 задач в минуту
            'time_limit': 1800,   # Таймаут 30 минут
            'soft_time_limit': 1500,  # Мягкий таймаут 25 минут
        },
    },
    # Настройки воркеров для очереди анализа пористости
    task_acks_late=True,  # Подтверждаем задачи только после выполнения
)