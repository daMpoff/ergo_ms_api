"""
Основной конфигурационный файл Celery для Django-приложения.
Отвечает за инициализацию Celery, настройку периодических задач и автоматическое обнаружение задач.

Функциональность:
    - Инициализация Celery приложения
    - Настройка интеграции с Django
    - Автоматическое обнаружение задач из установленных приложений
    - Полное логирование в файлы
"""

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

from src.core.utils.auto_api.auto_config import get_env_deploy_type

# Настройки логирования для Celery
import logging
from logging.handlers import RotatingFileHandler

# Определение типа развертывания и настройка переменной окружения Django
deploy_type = get_env_deploy_type()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', deploy_type)

# Инициализация Celery приложения
celery_app = Celery('src')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Настройка логирования Celery
def setup_celery_logging():
    """Настраивает логирование для Celery"""
    import os
    
    # Создаем директорию для логов если её нет
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Пути к файлам логов
    celery_log_file = os.path.join(log_dir, 'celery.log')
    celery_worker_log_file = os.path.join(log_dir, 'celery_worker.log')
    celery_beat_log_file = os.path.join(log_dir, 'celery_beat.log')
    celery_tasks_log_file = os.path.join(log_dir, 'celery_tasks.log')
    
    # Настройка форматтера для логов
    log_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Основной логгер Celery
    celery_logger = logging.getLogger('celery')
    celery_logger.setLevel(logging.DEBUG)
    
    # Хендлер для файла
    celery_file_handler = RotatingFileHandler(
        celery_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    celery_file_handler.setLevel(logging.DEBUG)
    celery_file_handler.setFormatter(log_formatter)
    celery_logger.addHandler(celery_file_handler)
    
    # Логгер для воркеров
    worker_logger = logging.getLogger('celery.worker')
    worker_logger.setLevel(logging.DEBUG)
    
    worker_file_handler = RotatingFileHandler(
        celery_worker_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    worker_file_handler.setLevel(logging.DEBUG)
    worker_file_handler.setFormatter(log_formatter)
    worker_logger.addHandler(worker_file_handler)
    
    # Логгер для beat (планировщик)
    beat_logger = logging.getLogger('celery.beat')
    beat_logger.setLevel(logging.DEBUG)
    
    beat_file_handler = RotatingFileHandler(
        celery_beat_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    beat_file_handler.setLevel(logging.DEBUG)
    beat_file_handler.setFormatter(log_formatter)
    beat_logger.addHandler(beat_file_handler)
    
    # Логгер для задач
    tasks_logger = logging.getLogger('celery.task')
    tasks_logger.setLevel(logging.DEBUG)
    
    tasks_file_handler = RotatingFileHandler(
        celery_tasks_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    tasks_file_handler.setLevel(logging.DEBUG)
    tasks_file_handler.setFormatter(log_formatter)
    tasks_logger.addHandler(tasks_file_handler)
    
    # Логгер для брокера
    broker_logger = logging.getLogger('kombu')
    broker_logger.setLevel(logging.INFO)
    
    broker_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'celery_broker.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    broker_file_handler.setLevel(logging.INFO)
    broker_file_handler.setFormatter(log_formatter)
    broker_logger.addHandler(broker_file_handler)
    
    # Отключаем вывод в консоль для продакшена
    if os.environ.get('DJANGO_SETTINGS_MODULE') == 'src.settings.production':
        # В продакшене только файловое логирование
        pass
    else:
        # В разработке добавляем консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_formatter)
        celery_logger.addHandler(console_handler)
        worker_logger.addHandler(console_handler)
        beat_logger.addHandler(console_handler)
        tasks_logger.addHandler(console_handler)

# Настраиваем логирование Celery
setup_celery_logging()

# Настройка пути к файлу состояния планировщика и периодических задач
celery_app.conf.update(
    beat_schedule_filename="celery/celerybeat-schedule",
    broker_url='sqla+sqlite:///celerydb.sqlite',
    result_backend='db+sqlite:///results.sqlite',
    task_routes={
        'src.modules.analysis_porosity.tasks.*': {'queue': 'porosity_analysis'},
        'src.modules.video_analysis.tasks.*': {'queue': 'video_analysis'},
    },
    task_default_queue='default',
    task_queues={
        'default': {},
        'porosity_analysis': {
            'exchange': 'porosity_analysis',
            'routing_key': 'porosity_analysis',
        },
        'video_analysis': {
            'exchange': 'video_analysis',
            'routing_key': 'video_analysis',
        },
    },
    # Настройки для задач анализа пористости (ограничения сняты)
    task_annotations={
        'src.modules.analysis_porosity.tasks.run_porosity_analysis': {
            'time_limit': 3600,   # Увеличен таймаут до 1 часа
            'soft_time_limit': 3300,  # Мягкий таймаут 55 минут
        },
        'src.modules.video_analysis.tasks.translate_video_analysis': {
            'time_limit': 7200,   # Таймаут 2 часа для команды перевода
            'soft_time_limit': 6900,  # Мягкий таймаут 1 час 55 минут
        },
        'src.modules.vacancies_parser.headhunter.tasks.parse_hh_vacancies_task': {
            'time_limit': 7200,   # Таймаут 2 часа для команды перевода
            'soft_time_limit': 6900,  # Мягкий таймаут 1 час 55 минут
        },
        'src.modules.vacancies_parser.headhunter.tasks.parse_single_vacancy_task': {
            'time_limit': 7200,   # Таймаут 2 часа для команды перевода
            'soft_time_limit': 6900,  # Мягкий таймаут 1 час 55 минут
        },
    },
    # Настройки воркеров для очереди анализа пористости
    task_acks_late=True,  # Подтверждаем задачи только после выполнения
    
    # Настройки логирования Celery
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    worker_log_color=False,
    worker_redirect_stdouts=False,
    worker_redirect_stdouts_level='INFO',
)