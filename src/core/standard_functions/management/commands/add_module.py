import os

from textwrap import dedent

from django.core.management.base import BaseCommand
from django.core.management.commands.startapp import Command as StartAppCommand

class Command(BaseCommand):
    help = 'Создание нового Django приложения в директории src/external_modules'

    def add_arguments(self, parser):
        parser.add_argument('name', help='Имя приложения')

    def handle(self, *args, **options):
        app_name = options['name']
        directory = 'src/external_modules'

        # Убедитесь, что целевая директория существует
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Сохраните текущую рабочую директорию
        original_cwd = os.getcwd()

        # Измените рабочую директорию на целевую директорию
        os.chdir(directory)

        # Вызовите оригинальную команду startapp
        startapp_command = StartAppCommand()
        startapp_command.run_from_argv(['manage.py', 'startapp', app_name])

        # Сгенерируйте содержимое файла apps.py
        app_config_name = f'src.external_modules.{app_name}'
        apps_py_content = dedent(f"""
        from django.apps import AppConfig

        class {app_name.capitalize()}Config(AppConfig):
            default_auto_field = 'django.db.models.BigAutoField'
            name = '{app_config_name}'
        """)

        # Восстановите оригинальную рабочую директорию
        os.chdir(original_cwd)

        # Запишите содержимое файла apps.py в файл
        apps_py_path = os.path.join(directory, app_name, 'apps.py')
        with open(apps_py_path, 'w') as f:
            f.write(apps_py_content.strip())

        # Выведите сообщение об успешном создании приложения
        self.stdout.write(self.style.SUCCESS(f'Приложение {app_name} успешно создано по пути - {directory}'))