"""
Файл содержащий конфигурацию логирования для Django-приложения.
Он включает настройки форматирования, обработчиков и логгеров для записи логов в файл и консоль.
"""

import os

from src.config.settings.static import LOGS_ROOT

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
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },

        # Простой форматтер, включающий только уровень логирования и сообщение.
        'simple': {
            'format': '{levelname} {message}',
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
        # Логгер для Django.
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        
        # Логгер для стандартных функций.
        'utils': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },

        # Логгер для Poetry скриптов.
        'scripts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}