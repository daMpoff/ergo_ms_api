import os
import importlib
import inspect

from django.apps import AppConfig
from django.urls import (
    include, 
    path
)

def discover_installed_apps(apps_dir):
    installed_apps = []

    def recursively_find_apps(current_dir, base_module):
        for app_name in os.listdir(current_dir):
            app_path = os.path.join(current_dir, app_name)
            if os.path.isdir(app_path):
                module_path = f'{base_module}.{app_name}'
                apps_py_path = os.path.join(app_path, 'apps.py')
                if os.path.exists(apps_py_path):
                    try:
                        app_module = importlib.import_module(f'src.{module_path}.apps')
                        app_config = None

                        for name, obj in inspect.getmembers(app_module, inspect.isclass):
                            if issubclass(obj, AppConfig) and obj is not AppConfig:
                                app_config = obj
                                break

                        if app_config:
                            installed_apps.append(f'src.{module_path}')
                    except ModuleNotFoundError:
                        print(f"Модуль не найден: {module_path}.apps")
                    except AttributeError:
                        print(f"Ошибка атрибута: {module_path}.apps не имеет допустимого класса AppConfig")
                else:
                    recursively_find_apps(app_path, module_path)

    recursively_find_apps(apps_dir, os.path.basename(apps_dir))

    return installed_apps

def discover_installed_app_urls(base_path):
    urlpatterns = []
    # Получаем список всех подпапок в base_path
    for module_name in os.listdir(base_path):
        module_path = os.path.join(base_path, module_name)
        # Проверяем, является ли подпапка директорией
        if os.path.isdir(module_path):
            # Формируем путь для include
            url_pattern = path(f"external_modules/{module_name}/", include(f"src.external_modules.{module_name}.urls"))
            urlpatterns.append(url_pattern)

    return urlpatterns