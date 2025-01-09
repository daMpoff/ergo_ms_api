import os
from textwrap import dedent

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Создание нового Django приложения в директории src/external_modules без файла admin.py'

    def add_arguments(self, parser):
        parser.add_argument('name', help='Имя приложения')

    def handle(self, *args, **options):
        app_name = options['name']
        directory = 'src/external_modules'

        # Убедитесь, что целевая директория существует
        if not os.path.exists(directory):
            os.makedirs(directory)

        app_directory = os.path.join(directory, app_name)
        app_directory = os.path.normpath(app_directory)
        
        # Проверка существования модуля
        if os.path.exists(app_directory):
            self.stdout.write(self.style.ERROR(f'Приложение {app_name} уже существует по пути - {app_directory}'))
            return

        # Создайте структуру директорий для нового приложения
        os.makedirs(app_directory)
        os.makedirs(os.path.join(app_directory, 'migrations'))

        # Создайте файлы для нового приложения
        files_to_create = {
            '__init__.py': '',
            'apps.py': dedent(f"""
                from django.apps import AppConfig

                class {app_name.capitalize()}Config(AppConfig):
                    default_auto_field = 'django.db.models.BigAutoField'
                    name = 'src.external_modules.{app_name}'
            """),
            'models.py': '',
            'tests.py': '',
            'views.py': '',
            'urls.py': dedent("""
                from django.urls import (
                    path
                )

                urlpatterns = [
                ]
            """),
            'migrations/__init__.py': '',
        }

        for filename, content in files_to_create.items():
            file_path = os.path.join(app_directory, filename)
            with open(file_path, 'w') as f:
                f.write(content.strip())

        # Выведите сообщение об успешном создании приложения
        self.stdout.write(self.style.SUCCESS(f'Приложение {app_name} успешно создано по пути - {directory}'))