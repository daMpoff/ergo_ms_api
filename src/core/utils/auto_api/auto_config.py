"""
Файл с функциями для автоматизации сборки Django приложений (модулей).
"""

import os
import re
import importlib
import inspect
import logging

from typing import List

from django.apps import AppConfig
from django.urls import (
    include, 
    path
)

from src.config.env import env

logger = logging.getLogger('utils')

def discover_installed_apps(apps_dir: str) -> List[str]:
    """
    Рекурсивно обходит директории и находит установленные приложения, включая подмодули.
    Аргументы:
        apps_dir (str): Базовая директория, в которой находятся приложения.
    Возвращает:
        list: Список строк, представляющих пути к установленным приложениям.
    """
    installed_apps = []

    def recursively_find_apps(current_dir: str, base_module: str) -> None:
        """
        Рекурсивно обходит директории и находит установленные приложения, включая подмодули.
        Аргументы:
            current_dir (str): Текущая директория для обхода.
            base_module (str): Базовый модуль для текущей директории.
        """
        for app_name in os.listdir(current_dir):
            app_path = os.path.join(current_dir, app_name)

            # Проверяем, является ли это директорией
            if os.path.isdir(app_path):
                module_path = f'{base_module}.{app_name}' if base_module else app_name

                # Проверяем наличие файла apps.py
                apps_py_path = os.path.join(app_path, 'apps.py')
                if os.path.exists(apps_py_path):
                    try:
                        # Пытаемся импортировать модуль apps
                        app_module = importlib.import_module(f'src.{module_path}.apps')

                        # Ищем класс AppConfig
                        app_config = None
                        for name, obj in inspect.getmembers(app_module, inspect.isclass):
                            if issubclass(obj, AppConfig) and obj is not AppConfig:
                                app_config = obj
                                break

                        if app_config:
                            installed_apps.append(f'src.{module_path}')
                            logger.debug(f"Найдено приложение: {module_path}")
                    except ModuleNotFoundError:
                        logger.error("Модуль не найден: %s.apps", module_path)
                    except AttributeError:
                        logger.error("Ошибка атрибута: %s.apps не имеет допустимого класса AppConfig", module_path)
                
                # Продолжаем рекурсивный обход независимо от наличия apps.py
                recursively_find_apps(app_path, module_path)

    # Начинаем обход с базовой директории
    recursively_find_apps(apps_dir, os.path.basename(apps_dir))
    
    return installed_apps

def discover_installed_app_urls(apps_dir: str, prefix: str = None) -> List[str]:
    """
    Рекурсивно обходит директории и находит URL-конфигурации для установленных приложений.

    Аргументы:
        apps_dir (str): Базовая директория, в которой находятся приложения.
        prefix (str): Префикс для импорта модулей (например, "src").

    Возвращает:
        list: Список URL-конфигураций для установленных приложений.
    """
    urlpatterns = []

    def recursively_find_urls(current_dir: str, current_prefix: str) -> None:
        """
        Рекурсивно обходит директории и находит URL-конфигурации.

        Аргументы:
            current_dir (str): Текущая директория для обхода.
            current_prefix (str): Текущий префикс для импорта модулей.
        """
        for module_name in os.listdir(current_dir):
            module_path = os.path.join(current_dir, module_name)
            if os.path.isdir(module_path):
                # Проверяем, является ли папка Python-пакетом (имеет __init__.py)
                init_py_path = os.path.join(module_path, '__init__.py')
                if os.path.exists(init_py_path):
                    # Формируем полный путь к модулю
                    module_full_path = f"{current_prefix}.{module_name}" if current_prefix else module_name

                    # Проверяем наличие файла urls.py
                    urls_py_path = os.path.join(module_path, 'urls.py')
                    if os.path.exists(urls_py_path):
                        # Формируем маршрут и добавляем его в urlpatterns
                        route = f"{module_name}/"
                        url_pattern = path(route, include(f"{module_full_path}.urls"))
                        urlpatterns.append(url_pattern)

                    # Рекурсивно обходим подмодули
                    recursively_find_urls(module_path, module_full_path)

    # Начинаем рекурсивный поиск
    recursively_find_urls(apps_dir, prefix)

    return urlpatterns

def check_app_config_name(directory: str, config_name: str) -> bool:
    """
    Проверяет все файлы apps.py в указанной директории на наличие определенного названия конфига.

    Аргументы:
        directory (str): Директория, в которой находятся файлы apps.py.
        config_name (str): Название конфига, которое нужно проверить.

    Возвращает:
        bool: True, если конфиг найден, иначе False.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == 'apps.py':
                file_path = os.path.join(root, file)

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                    searched_class_signature = rf'class\s+{config_name}Config\s*\(AppConfig\):'
                    if re.search(searched_class_signature, content):
                        return True
    return False

def get_env_deploy_type():
    development = 'src.config.patterns.development'
    production = 'src.config.patterns.production'

    deploy_type = env.str('API_DEPLOY_TYPE', default='development')

    if deploy_type == 'production':
        return production
    else:
        return development