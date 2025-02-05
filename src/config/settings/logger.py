"""
Файл содержащий конфигурацию логирования для Django-приложения.
Он включает настройки форматирования, обработчиков и логгеров для записи логов в файл и консоль.
"""

import os

from src.config.settings.static import LOGS_ROOT

# Создаем директорию для логов, если она не существует
os.makedirs(LOGS_ROOT, exist_ok=True)

# Проверяем права на запись
log_file = os.path.join(LOGS_ROOT, 'debug.log')
try:
    with open(log_file, 'a') as f:
        # Записываем пустую строку в файл
        f.write('')
except Exception as e:
    print(f"ОШИБКА: Невозможно записать в файл лога {log_file}: {str(e)}")
    raise

# Конфигурация логирования для Django-приложения.
LOGGING = {
    # Версия конфигурации логирования.
    'version': 1,

    # Флаг, указывающий, отключать ли существующие логгеры.
    'disable_existing_loggers': False,

    # Форматтеры для логов.
    'formatters': {
        # Подробный форматтер, включающий уровень логирования, время, модуль и сообщение.
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },

        # Простой форматтер, включающий только уровень логирования и сообщение.
        'simple': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
    },

    # Обработчики для логов.
    'handlers': {
        # Обработчик для записи логов в файл.
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_ROOT, 'debug.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },

        # Обработчик для записи логов в консоль.
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    # Логгеры для различных частей приложения.
    'loggers': {
        # Корневой логгер
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'config': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'config.database': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'utils': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'scripts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}