"""
Файл для команды создания нового модуля в директории src/external.

Этот файл содержит Django команду для создания нового модуля в указанной директории.
Команда создает необходимую структуру директорий и файлов для нового модуля.

Пример использования:
>>> python manage.py add_module my_new_app
"""

import os
from textwrap import dedent

from django.core.management.base import BaseCommand
from django.conf import settings

from src.config.auto_config import check_app_config_name
from src.core.utils.methods import convert_snake_to_camel

class Command(BaseCommand):
    """
    Класс Django команды для создания нового модуля.

    Атрибуты:
        help (str): Описание команды.
    """
    help = 'Создание нового модуля в директории src/external'

    def add_arguments(self, parser):
        """
        Добавляет аргументы для команды.

        Аргументы:
            parser (argparse.ArgumentParser): Объект парсера аргументов.
        """
        parser.add_argument('name', help='Имя модуля')

    def handle(self, *args, **options):
        """
        Основной метод для выполнения команды.

        Аргументы:
            *args: Дополнительные аргументы.
            **options: Опции команды.
        """
        module_name = options['name']

        external_modules_directory = getattr(settings, 'EXTERNAL_MODULES_DIR', None)

        # Проверка на наличие целевой директории
        if not os.path.exists(external_modules_directory):
            os.makedirs(external_modules_directory)

        module_directory = os.path.join(external_modules_directory, module_name)
        module_directory = os.path.normpath(module_directory)

        # Проверка существования модуля
        if os.path.exists(module_directory):
            self.stdout.write(self.style.ERROR(f'Модуль {module_name} уже существует по пути - {module_directory}.'))
            return
        
        camel_module_name = convert_snake_to_camel(module_name)
        if check_app_config_name(external_modules_directory, camel_module_name):
            self.stdout.write(self.style.ERROR(f'Уже существует модуль c именем класса конфига - {camel_module_name}Config.'))
            self.stdout.write(self.style.ERROR(f'Попробуйте другое название модуля.'))
            return

        # Создание структуры директорий для нового приложения
        os.makedirs(module_directory)
        os.makedirs(os.path.join(module_directory, 'migrations'))

        # Создание файлов для нового приложения
        files_to_create = {
            '__init__.py': dedent(f"""
                import configparser

                config = configparser.ConfigParser()

                MODULE_PATH = 'src/external/{module_name}/'
                CONF_PATH = MODULE_PATH + '.conf'

                config.read(CONF_PATH)
            """),
            'apps.py': dedent(f"""
                from django.apps import AppConfig

                class {camel_module_name}Config(AppConfig):
                    default_auto_field = 'django.db.models.BigAutoField'
                    name = 'src.external.{module_name}'
            """),
            'urls.py': dedent("""
                from django.urls import (
                    path
                )

                urlpatterns = [
                ]
            """),
            '.conf': dedent(f"""
                [Main]
                module_name = {module_name}
            """),
            'models.py': dedent("""
                from django.db import models

                # Создавайте свои модели здесь.
            """),
            'scripts.py': dedent("""
                # Создавайте свои скрипты здесь.
            """),
            'tests.py': dedent("""
                from django.test import TestCase

                # Создавайте свои тесты здесь.
            """),
            'serializers.py': dedent("""
                from rest_framework import serializers

                # Создавайте свои сериализаторы здесь.
            """),
            'methods.py': dedent("""
                # Создавайте свои вспомогательные методы здесь.
            """),
            'views.py': dedent("""
                from django.shortcuts import render

                # Создавайте свои API методы здесь.
            """),
            'migrations/__init__.py': dedent(f"""
            """),
        }

        for filename, content in files_to_create.items():
            file_path = os.path.join(module_directory, filename)
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content.strip())

        # Вывод сообщения об успешном создании модуля
        self.stdout.write(self.style.SUCCESS(f'Модуль {module_name} успешно создано по пути - {module_directory}'))