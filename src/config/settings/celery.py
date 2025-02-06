"""
Файл содержащий конфигурацию Celery для Django-приложения.
Включает настройки брокера сообщений Redis, сериализации задач и временной зоны.

Настройки:
    CELERY_BROKER_URL: URL-адрес брокера сообщений Redis
    CELERY_RESULT_BACKEND: URL-адрес бэкенда для хранения результатов задач
    CELERY_ACCEPT_CONTENT: Список разрешенных форматов сериализации
    CELERY_TASK_SERIALIZER: Формат сериализации для задач
    CELERY_RESULT_SERIALIZER: Формат сериализации для результатов
    CELERY_TIMEZONE: Временная зона для планировщика задач
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: Флаг повторного подключения к брокеру при запуске
    
    REDIS_PATH: Путь к исполняемому файлу Redis сервера
"""

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

REDIS_PATH = r"\redis\redis-server.exe"