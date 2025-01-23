from rest_framework.renderers import (
    JSONRenderer,
    BrowsableAPIRenderer,
    StaticHTMLRenderer,
    TemplateHTMLRenderer
)

# Путь к файлу конфигурации интеграции
INTEGRATION_CONFIG_PATH = 'src/config/integration_config.yaml'

# Базовый путь для обработчиков
STANDARD_HANDLERS_PATH = 'src.handlers.'

# Суффикс для методов обработчиков
HANDLER_METHOD_NAME = '.handler'

# Словарь доступных рендереров
AVAILABLE_RENDERERS = {
    'json': JSONRenderer,
    'browsable': BrowsableAPIRenderer,
    'html': StaticHTMLRenderer,
    'template': TemplateHTMLRenderer
}

# Настройки Swagger
INTEGRATION_SWAGGER_SETTINGS = {
    'DEFAULT_TAG': 'Интеграция модулей',
    'DEFAULT_RENDERER': 'json',
    'FILE_PARAM_NAME': 'file',
}