import configparser
import importlib

from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response

# Загрузка функции-обработчика из модуля
def load_handler(handler_path):
    module_name, func_name = handler_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)

# Загрузка конфигурации из файла
def load_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

# Создание APIView на основе конфигурации
def create_api_view(name, config):
    path = config.get(name, "path")
    handler_path = config.get(name, "handler")
    methods = config.get(name, "methods").split(",")
    parameters = eval(config.get(name, "parameters", fallback="[]"))
    status_code = int(config.get(name, "status_code"))

    # Загрузка обработчика
    handler = load_handler(handler_path)

    # Динамическое создание APIView
    class DynamicAPIView(APIView):
        def get(self, request, *args, **kwargs):
            if "GET" in methods:
                data = handler(*parameters)
                return Response(data, status=status_code)

    # Назначение имени классу для читаемости
    DynamicAPIView.__name__ = name
    return path, DynamicAPIView

# Генерация маршрутов на основе конфигурации
def generate_routes_from_config(config_path):
    config = load_config(config_path)
    routes = []

    for section in config.sections():
        path_s, view = create_api_view(section, config)
        routes.append(path(path_s, view.as_view()))

    return routes
