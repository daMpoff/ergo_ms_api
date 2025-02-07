"""
Модуль для создания подмодулей внутри существующих модулей Django.

Этот модуль предоставляет команду Django для создания новых подмодулей
внутри существующих модулей в директории src/external.

Пример использования:
    python manage.py add_submodule existing_module new_submodule

Создает следующую структуру:
    src/external/existing_module/new_submodule/
    ├── __init__.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── serializers.py
    └── tests.py
"""

import os
import logging

from typing import Any, Dict
from textwrap import dedent

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

# Настройка логгера
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Команда Django для создания нового подмодуля внутри существующего модуля.

    Attributes:
        help (str): Описание команды для справки Django.
    """
    help = 'Создание нового подмодуля внутри существующего модуля'

    def add_arguments(self, parser) -> None:
        """
        Добавляет аргументы командной строки для команды.

        Args:
            parser: Парсер аргументов Django.
        """
        parser.add_argument('module_name', type=str, help='Имя существующего модуля')
        parser.add_argument('submodule_name', type=str, help='Имя создаваемого подмодуля')

    def create_file_structure(self, submodule_path: str, files_to_create: Dict[str, str]) -> None:
        """
        Создает файловую структуру подмодуля.

        Args:
            submodule_path (str): Путь к директории подмодуля
            files_to_create (Dict[str, str]): Словарь с именами файлов и их содержимым
        """
        for filename, content in files_to_create.items():
            file_path = os.path.join(submodule_path, filename)
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content.strip())
                logger.debug(f'Создан файл: {file_path}')
            except IOError as e:
                logger.error(f'Ошибка при создании файла {file_path}: {str(e)}')
                raise CommandError(f'Не удалось создать файл {filename}')

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Выполняет команду создания подмодуля.

        Args:
            *args: Позиционные аргументы
            **options: Именованные аргументы, включая module_name и submodule_name

        Raises:
            CommandError: Если модуль не существует или подмодуль уже существует
        """
        submodule_name = options['submodule_name']
        module_name = options['module_name']

        external_modules_directory = getattr(settings, 'EXTERNAL_MODULES_DIR', None)
        module_path = os.path.join(external_modules_directory, module_name)
        
        logger.info(f'Начало создания подмодуля {submodule_name} в модуле {module_name}')

        if not os.path.exists(module_path):
            logger.error(f'Модуль {module_name} не существует в {external_modules_directory}')
            raise CommandError(f'Модуль "{module_name}" не существует в {external_modules_directory}')

        submodule_path = os.path.join(module_path, submodule_name)

        if os.path.exists(submodule_path):
            logger.error(f'Подмодуль {submodule_name} уже существует в модуле {module_name}')
            raise CommandError(f'Подмодуль "{submodule_name}" уже существует в модуле "{module_name}"')

        try:
            os.makedirs(submodule_path)
            logger.debug(f'Создана директория подмодуля: {submodule_path}')

            files_to_create = {
                '__init__.py': '',
                'models.py': dedent("""
                    from django.db import models

                    # Создавайте свои модели здесь
                """),
                'views.py': dedent("""
                    from django.shortcuts import render

                    # Создавайте свои представления здесь
                """),
                'urls.py': dedent("""
                    from django.urls import path

                    urlpatterns = [
                    ]
                """),
                'serializers.py': dedent("""
                    from rest_framework import serializers

                    # Создавайте свои сериализаторы здесь
                """),
                'tests.py': dedent("""
                    from django.test import TestCase

                    # Создавайте свои тесты здесь
                """),
            }

            self.create_file_structure(submodule_path, files_to_create)
            
            logger.info(f'Подмодуль {submodule_name} успешно создан в модуле {module_name}')
            self.stdout.write(
                self.style.SUCCESS(
                    f'Подмодуль "{submodule_name}" успешно создан в модуле "{module_name}"'
                )
            )

        except Exception as e:
            logger.error(f'Ошибка при создании подмодуля: {str(e)}')
            raise CommandError(f'Не удалось создать подмодуль: {str(e)}')
