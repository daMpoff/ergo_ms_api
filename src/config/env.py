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
import logging

from src.config.settings.static import ENV_FILE_PATH
from src.core.utils.environment.methods import collect_env_files_from_configs

logger = logging.getLogger(__name__)

# Собираем переменные из всех .env файлов в папке configs
configs_env_vars = collect_env_files_from_configs()

# Инициализация объекта для работы с переменными окружения
env = environ.Env()

# Отслеживаем переменные, загруженные из основного .env файла
main_env_vars = set()

# Сначала загружаем основной .env файл (если существует)
if os.path.exists(ENV_FILE_PATH):
    # Читаем основной .env файл и отслеживаем его переменные
    with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key = line.split('=', 1)[0].strip()
                main_env_vars.add(key)
    environ.Env.read_env(ENV_FILE_PATH)

# Затем добавляем переменные из configs (они имеют приоритет)
if configs_env_vars:
    overridden_vars = []
    for key, value in configs_env_vars.items():
        # Проверяем, была ли переменная определена в основном .env файле
        if key in main_env_vars:
            overridden_vars.append(key)
        os.environ[key] = value
    
    # Логируем только если есть переопределения
    if overridden_vars:
        logger.warning(f"⚠️  Переменные из configs переопределили {len(overridden_vars)} переменных из основного .env:")
        for var in overridden_vars:
            logger.warning(f"  - {var}")