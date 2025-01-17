"""
Файл конфигурации Django приложения standard_functions.

Этот файл содержит класс конфигурации приложения, который определяет основные настройки,
такие как имя приложения и настройки базы данных по умолчанию.

Класс `StandardFunctionsConfig`:
    Определяет конфигурацию приложения standard_functions, включая:
    - Тип поля первичного ключа по умолчанию
    - Имя приложения в системе
"""

from django.apps import AppConfig

class StandardFunctionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.core.standard_functions'