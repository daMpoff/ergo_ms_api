import os
import shutil

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Очистка python кэша.'

    def handle(self, *args, **kwargs):
        root_directory = '.'

        for root, dirs, _ in os.walk(root_directory):
            for dir_name in dirs:
                if dir_name == '__pycache__':
                    dir_path = os.path.join(root, dir_name)

                    shutil.rmtree(dir_path)

                    self.stdout.write(self.style.SUCCESS(f'Удаленный файл: {dir_path}'))