import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.conf import settings

from src.modules.impuls_analysis.tasks import import_impuls_excel


logger = logging.getLogger('impuls_analysis')


class Command(BaseCommand):
    help = 'Импорт Excel-файла (расчет силы/план эксперимента) в таблицы через Celery.'

    def add_arguments(self, parser):
        parser.add_argument('--type', required=True, choices=['force', 'plan'], help='Тип файла: force | plan')
        parser.add_argument('--file', dest='file', required=True, help='Имя файла в media/impuls_analysis/input_files или абсолютный путь')
        # Старое поведение удалено: всегда используем Celery

    def handle(self, *args, **options):
        file_type = options['type']
        file_name = options['file']

        input_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
        if not os.path.isdir(input_dir):
            raise CommandError(f'Директория с входными файлами не найдена: {input_dir}')

        # Определяем путь к файлу
        input_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
        if os.path.isabs(file_name):
            file_path = file_name
        else:
            file_path = os.path.join(input_dir, file_name)

        if not os.path.exists(file_path):
            raise CommandError(f'Файл не найден: {file_path}')

        # Запускаем Celery импорт
        async_result = import_impuls_excel.delay(file_path, file_type)
        self.stdout.write(self.style.SUCCESS(
            f'Импорт запущен (task_id={async_result.id}). Файл: {file_path}, тип: {file_type}'
        ))

        # Ожидание статуса не реализуем — импорт id возвращён Celery


