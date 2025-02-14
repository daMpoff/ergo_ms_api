"""
Основной конфигурационный файл Celery для Django-приложения.
Отвечает за инициализацию Celery, настройку периодических задач и автоматическое обнаружение задач.

Функциональность:
    - Инициализация Celery приложения
    - Настройка интеграции с Django
    - Автоматическое обнаружение задач из установленных приложений
"""

import os

from celery import Celery

from django.conf import settings

from src.core.utils.auto_api.auto_config import get_env_deploy_type

# Определение типа развертывания и настройка переменной окружения Django
deploy_type = get_env_deploy_type()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', deploy_type)

# Инициализация Celery приложения
celery_app = Celery('src')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Настройка пути к файлу состояния планировщика
celery_app.conf.update(
    beat_schedule_filename="celery/celerybeat-schedule",
    broker_url='sqla+sqlite:///celerydb.sqlite',
    result_backend='db+sqlite:///results.sqlite',
)