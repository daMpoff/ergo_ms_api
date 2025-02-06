"""
Файл объединяющий локальные настройки для Django-приложения.

Он импортирует и объединяет настройки из различных модулей конфигурации, таких как базовые настройки,
настройки приложений, аутентификации, CORS, базы данных, локализации, статических файлов, логирования,
сервера, шаблонов и SMTP.
"""

from src.config.settings.base import *
from src.config.settings.apps import *
from src.config.settings.static import *
from src.config.settings.logger import *
from src.config.settings.auth import *
from src.config.settings.cors import *
from src.config.settings.database import *
from src.config.settings.localization import *
from src.config.settings.server import *
from src.config.settings.templates import *
from src.config.settings.smtp import *
from src.config.settings.auto_api import *
from src.config.settings.swagger import *
from src.config.settings.celery import *