"""
Файл для загрузки переменных окружения из .env файла для Django-приложения.

Функциональность:
    - Загрузка переменных окружения из .env файла
    - Предоставление доступа к переменным окружения через объект env
    - Автоматическое преобразование типов данных переменных окружения

Структура:
    ENV_DIR: Путь к файлу .env, расположенному в корневой директории проекта
    env: Объект environ.Env для доступа к переменным окружения

Использование:
    from src.config.env import env
    
    DEBUG = env.bool('DEBUG', default=False)
    SECRET_KEY = env.str('SECRET_KEY')
    DATABASE_URL = env.db('DATABASE_URL')
"""

import environ
import os

from src.config.settings.base import SYSTEM_DIR

# Определение пути к файлу .env
ENV_DIR = os.path.join(SYSTEM_DIR, '.env')

# Инициализация объекта для работы с переменными окружения
env = environ.Env()
environ.Env.read_env(ENV_DIR)