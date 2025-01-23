"""
Файл для определения маршрутов URL для Django-API-приложения.

Он использует функцию `path` из `django.urls` для определения маршрутов и функцию `include`
для включения URL-конфигураций из других модулей. Также используется функция
`discover_installed_app_urls` для автоматического обнаружения и включения URL-конфигураций
из внешних модулей, находящихся в директории `EXTERNAL_MODULES_DIR`.
"""

from django.urls import (
    include,
    path
)

from src.config.settings.integration import INTEGRATION_CONFIG_PATH
from src.core.utils.integration.modules_integration import generate_routes_from_config

from src.config.auto_config import discover_installed_app_urls
from src.config.settings.apps import EXTERNAL_MODULES_DIR

urlpatterns = [
    path("cms/adp/", include("src.core.cms.adp.urls")),
    path("utils/", include("src.core.utils.urls")),
]

# Добавляем URL-конфигурации из внешних модулей, автоматически 
# обнаруженные в директории EXTERNAL_MODULES_DIR
external_modules_urlpatterns = discover_installed_app_urls(EXTERNAL_MODULES_DIR)
urlpatterns += external_modules_urlpatterns

config_urlpatterns = generate_routes_from_config(INTEGRATION_CONFIG_PATH)
urlpatterns += config_urlpatterns