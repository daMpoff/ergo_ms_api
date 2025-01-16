"""
Файл для загрузки переменных окружения из .env файла для использования в Django-приложении.

Используется библиотека django-environ для чтения переменных окружения из файла .env,
который находится в корневой директории системы.
"""

import environ
import os

from src.config.settings.base import BASE_DIR

ENV_DIR = os.path.join(BASE_DIR.parent.parent, '.env')

env = environ.Env()
environ.Env.read_env(ENV_DIR)