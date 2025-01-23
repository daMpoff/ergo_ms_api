"""
Модуль для динамического создания API эндпоинтов на основе конфигурации.
"""

import importlib
import yaml
import logging
from typing import Any, Dict, Tuple, Type, List

from django.urls import path
from django.http import FileResponse
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import NotFound, ValidationError

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

logger = logging.getLogger('utils')

# Настройки из конфига
class IntegrationSettings:
    """Класс для хранения настроек интеграции."""
    standard_handlers_path: str = getattr(settings, 'STANDARD_HANDLERS_PATH', '')
    handler_method_name: str = getattr(settings, 'HANDLER_METHOD_NAME', '')
    available_renderers: Dict = getattr(settings, 'AVAILABLE_RENDERERS', {})
    swagger_settings: Dict = getattr(settings, 'SWAGGER_SETTINGS', {})

def load_handler(handler_path: str) -> Any:
    """
    Загрузка функции-обработчика из модуля.
    
    Args:
        handler_path: Путь к обработчику
        
    Returns:
        Загруженный обработчик
    """
    path = f"{IntegrationSettings.standard_handlers_path}{handler_path}{IntegrationSettings.handler_method_name}"
    module_name, func_name = path.rsplit('.', 1)
    
    try:
        module = importlib.import_module(module_name)
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        logger.error("Ошибка при загрузке обработчика %s: %s", handler_path, e)
        raise

def load_config(config_path: str) -> Dict:
    """
    Загрузка конфигурации из файла.
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        Загруженная конфигурация
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except (yaml.YAMLError, IOError) as e:
        logger.error("Ошибка при загрузке конфигурации: %s", e)
        raise

class SwaggerSchemaBuilder:
    """Класс для построения схемы Swagger."""
    
    type_mapping = {
        'string': openapi.TYPE_STRING,
        'integer': openapi.TYPE_INTEGER,
        'boolean': openapi.TYPE_BOOLEAN,
        'file': openapi.TYPE_FILE,
        'array': openapi.TYPE_ARRAY,
        'object': openapi.TYPE_OBJECT,
    }

    @staticmethod
    def get_param_info(param_value: Any) -> Dict[str, str]:
        """Получает информацию о параметре в унифицированном формате."""
        if isinstance(param_value, dict):
            return {
                'description': param_value.get('description', ''),
                'type': param_value.get('type', 'string')
            }
        return {'description': param_value, 'type': 'string'}

    @classmethod
    def create_file_parameter(cls) -> openapi.Parameter:
        """Создает параметр для загрузки файла."""
        return openapi.Parameter(
            name=IntegrationSettings.swagger_settings['FILE_PARAM_NAME'],
            in_=openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description='Файл для загрузки'
        )

    @classmethod
    def create_parameters(cls, method: str, params_desc: Dict[str, Any],
                         required_params: List[str], optional_params: Dict[str, Any]) -> List[openapi.Parameter]:
        """Создает параметры для swagger документации."""
        if method in ["POST", "PUT", "PATCH"] and 'file' in required_params:
            return [cls.create_file_parameter()]

        if method in ["POST", "PUT", "PATCH"]:
            return cls.create_body_parameter(params_desc, required_params, optional_params)
        
        return cls.create_query_parameters(params_desc, required_params)

    @classmethod
    def create_body_parameter(cls, params_desc: Dict, required_params: List[str],
                            optional_params: Dict) -> List[openapi.Parameter]:
        """Создает параметры для тела запроса."""
        properties = {}
        required = []

        for param_name, param_value in params_desc.items():
            param_info = cls.get_param_info(param_value)
            if param_name in required_params:
                required.append(param_name)

            param_type = cls.type_mapping.get(param_info['type'], openapi.TYPE_STRING)
            properties[param_name] = openapi.Schema(
                type=param_type,
                description=param_info['description'],
                nullable=param_name in optional_params and optional_params[param_name] is None
            )

        schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=properties,
            required=required
        )

        return [openapi.Parameter(
            name='body',
            in_=openapi.IN_BODY,
            required=True,
            schema=schema
        )]

    @classmethod
    def create_query_parameters(cls, params_desc: Dict, required_params: List[str]) -> List[openapi.Parameter]:
        """Создает параметры для query-строки."""
        parameters = []
        for param_name, param_value in params_desc.items():
            param_info = cls.get_param_info(param_value)
            parameters.append(
                openapi.Parameter(
                    name=param_name,
                    in_=openapi.IN_QUERY,
                    description=param_info['description'],
                    required=param_name in required_params,
                    type=cls.type_mapping.get(param_info['type'], openapi.TYPE_STRING)
                )
            )
        return parameters

def create_handler_instance(handler_class, required_params, optional_params):
    """Создает экземпляр обработчика с параметрами из конфига."""
    return handler_class(required_params=required_params, optional_params=optional_params)

def create_swagger_parameters(method: str, params_desc: Dict[str, Any], 
                            required_params: list, optional_params: Dict[str, Any]):
    """Создает параметры для swagger документации."""
    parameters = []
    
    # Словарь соответствия типов из конфига к типам openapi
    type_mapping = {
        'string': openapi.TYPE_STRING,
        'integer': openapi.TYPE_INTEGER,
        'boolean': openapi.TYPE_BOOLEAN,
        'file': openapi.TYPE_FILE,
        'array': openapi.TYPE_ARRAY,
        'object': openapi.TYPE_OBJECT,
    }

    def get_param_info(param_name, param_value):
        """Получает информацию о параметре в унифицированном формате"""
        if isinstance(param_value, dict):
            return {
                'description': param_value.get('description', ''),
                'type': param_value.get('type', 'string')
            }
        return {
            'description': param_value,
            'type': 'string'
        }
    
    # Для POST запросов с файлами создаем специальный параметр
    if method in ["POST", "PUT", "PATCH"] and any(param == 'file' for param in required_params):
        file_info = get_param_info('file', params_desc.get('file', 'Файл для загрузки'))
        parameters.append(
            openapi.Parameter(
                name='file',
                in_=openapi.IN_FORM,
                description=file_info['description'],
                type=openapi.TYPE_FILE,
                required=True
            )
        )
        return parameters
    
    # Для обычных POST запросов создаем единую схему для тела запроса
    if method in ["POST", "PUT", "PATCH"]:
        properties = {}
        required = []
        
        for param_name, param_value in params_desc.items():
            param_info = get_param_info(param_name, param_value)
            is_required = param_name in required_params
            if is_required:
                required.append(param_name)
            
            param_type = type_mapping.get(param_info['type'], openapi.TYPE_STRING)
            
            if param_name in optional_params:
                default_value = optional_params[param_name]
                if default_value is None:
                    properties[param_name] = openapi.Schema(type=param_type, nullable=True)
                    continue
            
            properties[param_name] = openapi.Schema(
                type=param_type,
                description=param_info['description']
            )
        
        body_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=properties,
            required=required
        )
        
        parameters.append(
            openapi.Parameter(
                name='body',
                in_=openapi.IN_BODY,
                required=True,
                schema=body_schema
            )
        )
    else:
        for param_name, param_value in params_desc.items():
            param_info = get_param_info(param_name, param_value)
            is_required = param_name in required_params
            param_type = type_mapping.get(param_info['type'], openapi.TYPE_STRING)
            
            parameters.append(
                openapi.Parameter(
                    name=param_name,
                    in_=openapi.IN_QUERY,
                    description=param_info['description'],
                    required=is_required,
                    type=param_type
                )
            )
    
    return parameters

class BaseDynamicAPIView(APIView):
    """Базовый класс для динамических API views"""
    
    method = None
    handler = None
    status_code = None
    
    def get_renderer_context(self):
        """Получение контекста для рендерера"""
        context = {
            'view': self,
            'args': getattr(self, 'args', ()),
            'kwargs': getattr(self, 'kwargs', {}),
            'request': getattr(self, 'request', None)
        }
        return context
    
    def get_renderer(self):
        """Получение рендерера в зависимости от типа запроса"""
        # Для браузерных запросов возвращаем browsable рендерер
        if self.request and 'text/html' in self.request.META.get('HTTP_ACCEPT', ''):
            browsable_renderers = [r for r in self.renderer_classes if getattr(r, 'format', None) == 'api']
            if browsable_renderers:
                return browsable_renderers[0]()
        
        # Для остальных запросов используем JSON рендерер
        json_renderers = [r for r in self.renderer_classes if getattr(r, 'format', None) == 'json']
        if json_renderers:
            return json_renderers[0]()
        
        # Если ничего не подошло, используем первый доступный рендерер
        return self.renderer_classes[0]()
        
    def dispatch(self, request, *args, **kwargs):
        """Обработка входящего запроса"""
        # Используем родительский dispatch для правильной инициализации
        self.args = args
        self.kwargs = kwargs
        self.headers = self.default_response_headers
        
        # Позволяем DRF инициализировать request
        request = super().initialize_request(request, *args, **kwargs)
        self.request = request

        try:
            if request.method == 'OPTIONS':
                response = self.options(request, *args, **kwargs)
            elif request.method != self.method:
                response = Response({"error": "Method not allowed"}, status=405)
            else:
                handler = self.get_handler()
                response = handler(request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)

        if isinstance(response, Response):
            response.accepted_renderer = self.get_renderer()
            response.accepted_media_type = response.accepted_renderer.media_type
            response.renderer_context = self.get_renderer_context()

        return response

    def options(self, request, *args, **kwargs):
        """Обработка OPTIONS запроса"""
        metadata = {
            'name': self.__class__.__name__,
            'description': self.__doc__,
            'renders': [renderer.media_type for renderer in self.renderer_classes],
            'parses': ['application/json'],
            'allowed_methods': [self.method, 'OPTIONS']
        }
        
        response = Response(metadata)
        response.accepted_renderer = self.get_renderer()
        response.accepted_media_type = response.accepted_renderer.media_type
        response.renderer_context = self.get_renderer_context()
        
        return response

    def get_handler(self):
        """Получение обработчика для текущего метода"""
        if self.method.lower() == 'get':
            return self.get
        elif self.method.lower() == 'post':
            return self.post
        elif self.method.lower() == 'put':
            return self.put
        elif self.method.lower() == 'patch':
            return self.patch
        elif self.method.lower() == 'delete':
            return self.delete
        return None

def create_dynamic_api_view(method, renderers, handler, status_code, 
                            swagger_description, swagger_params, swagger_responses):
    """Фабрика для создания классов DynamicAPIView"""
    class_name = f'DynamicAPIView_{method}'
    
    # Преобразуем responses из конфига в формат для swagger
    swagger_response_schemas = {}
    for status_code_str, response_info in swagger_responses.items():
        try:
            response_status = int(status_code_str)
            
            # Создаем схему для ответа
            if isinstance(response_info, dict) and 'example' in response_info:
                example_data = response_info['example']
                
                if example_data == 'binary_data':
                    # Для бинарных данных
                    properties = {
                        'file': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format='binary'
                        )
                    }
                elif isinstance(example_data, dict):
                    # Для JSON ответов
                    properties = {}
                    for key, value in example_data.items():
                        if isinstance(value, dict):
                            nested_properties = {
                                k: openapi.Schema(
                                    type=openapi.TYPE_STRING if isinstance(v, str) 
                                    else openapi.TYPE_INTEGER if isinstance(v, int)
                                    else openapi.TYPE_OBJECT,
                                    example=v
                                ) for k, v in value.items()
                            }
                            properties[key] = openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties=nested_properties
                            )
                        else:
                            properties[key] = openapi.Schema(
                                type=openapi.TYPE_STRING if isinstance(value, str)
                                else openapi.TYPE_INTEGER if isinstance(value, int)
                                else openapi.TYPE_OBJECT,
                                example=value
                            )
                    
                schema = openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=properties
                )
                
                swagger_response_schemas[response_status] = openapi.Response(
                    description=response_info.get('description', ''),
                    schema=schema,
                    examples={'application/json': example_data} if example_data != 'binary_data' else None
                )
            else:
                # Для ответов без примеров
                swagger_response_schemas[response_status] = openapi.Response(
                    description=response_info.get('description', '')
                )
                
        except (ValueError, TypeError) as e:
            logger.error("Ошибка при обработке response для кода %s: %s", status_code_str, e)
            continue

    class_attrs = {
        'renderer_classes': renderers,
        'method': method.upper(),
        'handler': staticmethod(handler),
        'default_status_code': status_code,
    }

    # Добавляем поддержку загрузки файлов для POST запросов
    if (method in ["POST", "PUT", "PATCH"] and 
        any(p.name == IntegrationSettings.swagger_settings['FILE_PARAM_NAME'] for p in swagger_params)):
        class_attrs['parser_classes'] = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description=swagger_description,
        manual_parameters=swagger_params,
        responses=swagger_response_schemas,
        tags=[IntegrationSettings.swagger_settings['DEFAULT_TAG']]
    )
    def method_func(self, request, *args, **kwargs):
        try:
            if method in ["GET", "DELETE"]:
                query_params = request.query_params.dict()
                response = self.handler(**query_params, **kwargs)
                if isinstance(response, FileResponse):
                    return response
                data = response
            elif method in ["POST", "PUT", "PATCH"]:
                if request.FILES:
                    data = self.handler(
                        **{IntegrationSettings.swagger_settings['FILE_PARAM_NAME']: request.FILES[IntegrationSettings.swagger_settings['FILE_PARAM_NAME']]}, 
                        **kwargs
                    )
                else:
                    body_data = request.data
                    data = self.handler(**body_data, **kwargs)
            else:
                return Response({"error": "Unsupported method"}, status=400)
            
            response = Response(data, status=self.default_status_code)
            response.accepted_renderer = self.get_renderer()
            response.accepted_media_type = response.accepted_renderer.media_type
            response.renderer_context = {}
            
            return response
            
        except NotFound as e:
            return Response({"error": str(e)}, status=404)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response(
                {"error": f"Внутренняя ошибка сервера: {str(e)}"}, 
                status=500
            )

    method_func.__name__ = method.lower()
    class_attrs[method.lower()] = method_func

    return type(class_name, (BaseDynamicAPIView,), class_attrs)

def create_api_view(name: str, config: dict) -> Tuple[str, Type[APIView]]:
    """Создает APIView на основе конфигурации."""
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
    
    renderers_str = endpoint_config.get("renderers", IntegrationSettings.swagger_settings['DEFAULT_RENDERER']).lower()
    renderer_names = [r.strip() for r in renderers_str.split(',')]
    renderers = [IntegrationSettings.available_renderers[r] for r in renderer_names if r in IntegrationSettings.available_renderers]
    
    if not renderers:
        renderers = [IntegrationSettings.available_renderers[IntegrationSettings.swagger_settings['DEFAULT_RENDERER']]]

    module_name = IntegrationSettings.standard_handlers_path + handler_path
    module = importlib.import_module(module_name)
    handler_class = getattr(module, 'HandlerClass')
    
    handler = create_handler_instance(handler_class, required_params, optional_params)

    swagger_params = create_swagger_parameters(
        method, params_description, required_params, optional_params
    )

    DynamicAPIView = create_dynamic_api_view(
        method=method,
        renderers=renderers,
        handler=handler,
        status_code=status_code,
        swagger_description=description,
        swagger_params=swagger_params,
        swagger_responses=responses
    )

    DynamicAPIView.__name__ = name
    
    return path, DynamicAPIView

def generate_routes_from_config(config_path: str) -> list:
    """Генерирует маршруты из конфигурации."""
    config = load_config(config_path)
    routes = []

    for section_name in config:
        path_s, view = create_api_view(section_name, config)
        routes.append(path(path_s, view.as_view()))

    return routes