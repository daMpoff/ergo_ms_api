import json
import configparser

import importlib
import yaml

from typing import Any, Dict

from django.urls import path

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import (
    JSONRenderer,
    BrowsableAPIRenderer,
    StaticHTMLRenderer,
    TemplateHTMLRenderer
)

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from src.config.serializer_generator import create_serializer_class

STANDARD_HANDLERS_PATH = 'src.handlers.'
HANDLER_METHOD_NAME = '.handler'

# Словарь доступных рендереров
AVAILABLE_RENDERERS = {
    'json': JSONRenderer,
    'browsable': BrowsableAPIRenderer,
    'html': StaticHTMLRenderer,
    'template': TemplateHTMLRenderer
}

# Загрузка функции-обработчика из модуля
def load_handler(handler_path):
    path = STANDARD_HANDLERS_PATH + handler_path + HANDLER_METHOD_NAME

    module_name, func_name = path.rsplit('.', 1)
    module = importlib.import_module(module_name)

    return getattr(module, func_name)

# Загрузка конфигурации из файла
def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def create_handler_instance(handler_class, required_params, optional_params):
    """Создает экземпляр обработчика с параметрами из конфига."""
    return handler_class(required_params=required_params, optional_params=optional_params)

def create_swagger_parameters(method: str, params_desc: Dict[str, str], 
                            required_params: list, optional_params: Dict[str, Any]):
    """Создает параметры для swagger документации."""
    parameters = []
    
    for param_name, param_desc in params_desc.items():
        is_required = param_name in required_params
        
        if method in ["GET", "DELETE"]:
            # Для GET и DELETE используем type вместо schema
            param_type = openapi.IN_QUERY
            param = openapi.Parameter(
                name=param_name,
                in_=param_type,
                description=param_desc,
                required=is_required,
                type=openapi.TYPE_STRING  # По умолчанию строка
            )
            
            # Определяем тип параметра если он есть в optional_params
            if param_name in optional_params:
                default_value = optional_params[param_name]
                if isinstance(default_value, int):
                    param.type = openapi.TYPE_INTEGER
                elif isinstance(default_value, bool):
                    param.type = openapi.TYPE_BOOLEAN
                elif default_value is None:
                    param.type = openapi.TYPE_STRING
                    param.x_nullable = True
            
            parameters.append(param)
        else:
            # Для POST, PUT, PATCH используем schema
            param_type = openapi.IN_BODY
            param_schema = None
            if param_name in optional_params:
                default_value = optional_params[param_name]
                if isinstance(default_value, int):
                    param_schema = openapi.Schema(type=openapi.TYPE_INTEGER)
                elif isinstance(default_value, bool):
                    param_schema = openapi.Schema(type=openapi.TYPE_BOOLEAN)
                elif default_value is None:
                    param_schema = openapi.Schema(type=openapi.TYPE_STRING, nullable=True)
                else:
                    param_schema = openapi.Schema(type=openapi.TYPE_STRING)
                    
            parameter = openapi.Parameter(
                name=param_name,
                in_=param_type,
                description=param_desc,
                required=is_required,
                schema=param_schema
            )
            parameters.append(parameter)
    
    return parameters

# Создание APIView на основе конфигурации
def create_api_view(name, config):
    endpoint_config = config[name]
    path = endpoint_config["path"]
    handler_path = endpoint_config["handler"]
    method = endpoint_config["method"]
    status_code = int(endpoint_config["status_code"])
    description = endpoint_config.get("description", "")
    
    required_params = endpoint_config.get("required_params", [])
    optional_params = endpoint_config.get("optional_params", {})
    params_description = endpoint_config.get("params_description", {})
    responses = endpoint_config.get("responses", {})
    
    # Получаем список рендереров из конфига
    renderers_str = endpoint_config.get("renderers", "json").lower()
    renderer_names = [r.strip() for r in renderers_str.split(',')]
    renderers = [AVAILABLE_RENDERERS[r] for r in renderer_names if r in AVAILABLE_RENDERERS]
    
    if not renderers:
        renderers = [JSONRenderer]

    # Загружаем класс обработчика
    module_name = STANDARD_HANDLERS_PATH + handler_path
    module = importlib.import_module(module_name)
    handler_class = getattr(module, 'HandlerClass')  # Предполагаем, что класс называется HandlerClass
    
    # Создаем экземпляр обработчика с параметрами из конфига
    handler = create_handler_instance(handler_class, required_params, optional_params)

    # Создаем параметры для swagger
    swagger_params = create_swagger_parameters(
        method, params_description, required_params, optional_params
    )

    # Создаем сериализатор на основе примера ответа
    response_example = responses.get(str(status_code), {}).get("example", {})
    response_serializer = create_serializer_class(f"{name}Response", response_example)
    
    # Создаем словарь с ответами для swagger
    swagger_responses = {
        status_code: response_serializer
    }

    # Динамическое создание APIView
    class DynamicAPIView(APIView):
        renderer_classes = renderers

        def dispatch(self, request, *args, **kwargs):
            # Разрешаем OPTIONS запросы
            if request.method == 'OPTIONS':
                return self.options(request, *args, **kwargs)
                
            # Проверяем остальные методы
            if request.method != method:
                return Response({"error": "Method not allowed"}, status=405)
            
            return super().dispatch(request, *args, **kwargs)

        def options(self, request, *args, **kwargs):
            """Обработка OPTIONS запроса."""
            metadata = {
                'name': self.__class__.__name__,
                'allowed_methods': [method],
                'renders': [renderer.media_type for renderer in renderers],
                'parses': ['application/json'],
            }

            response = Response(metadata)
            response.accepted_renderer = renderers[0]()
            response.accepted_media_type = renderers[0].media_type
            response.renderer_context = {}

            return response

    # Создаем метод с декоратором swagger
    @swagger_auto_schema(
        operation_description=description,
        manual_parameters=swagger_params,
        responses=swagger_responses
    )
    def method_func(self, request, method=method, *args, **kwargs):
        # Обрабатываем данные в зависимости от метода
        if method in ["GET", "DELETE"]:
            query_params = request.query_params.dict()
            data = handler(**query_params, **kwargs)
        elif method in ["POST", "PUT", "PATCH"]:
            body_data = request.data
            data = handler(**body_data, **kwargs)
        else:
            return Response({"error": "Unsupported method"}, status=400)
        
        return Response(data, status=status_code)

    # Присваиваем метод к классу
    method_func.__name__ = method.lower()  # Важно для swagger
    setattr(DynamicAPIView, method.lower(), method_func)

    # Назначение имени классу для читаемости
    DynamicAPIView.__name__ = name
    return path, DynamicAPIView

# Генерация маршрутов на основе конфигурации
def generate_routes_from_config(config_path):
    config = load_config(config_path)
    routes = []

    # Теперь проходим по ключам словаря вместо sections()
    for section_name in config:
        path_s, view = create_api_view(section_name, config)
        routes.append(path(path_s, view.as_view()))

    return routes