import os
import importlib
import inspect
from django.apps import AppConfig

def autoconfig(apps_dir):
    installed_apps = []

    def find_apps(current_dir, base_module):
        for app_name in os.listdir(current_dir):
            app_path = os.path.join(current_dir, app_name)
            if os.path.isdir(app_path):
                module_path = f'{base_module}.{app_name}'
                apps_py_path = os.path.join(app_path, 'apps.py')
                if os.path.exists(apps_py_path):
                    try:
                        app_module = importlib.import_module(f'{module_path}.apps')
                        app_config = None

                        for name, obj in inspect.getmembers(app_module, inspect.isclass):
                            if issubclass(obj, AppConfig) and obj is not AppConfig:
                                app_config = obj
                                break

                        if app_config:
                            installed_apps.append(module_path)
                    except ModuleNotFoundError:
                        print(f"Module not found: {module_path}.apps")
                    except AttributeError:
                        print(f"Attribute error: {module_path}.apps does not have a valid AppConfig class")
                else:
                    find_apps(app_path, module_path)  # Рекурсивный обход внутренних папок

    find_apps(apps_dir, os.path.basename(apps_dir))

    return installed_apps
