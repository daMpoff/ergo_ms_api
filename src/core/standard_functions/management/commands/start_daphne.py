from django.core.management.base import BaseCommand

from src.core.standard_functions.enums import LogLevel
from src.core.standard_functions.daphne import Daphne

class Command(BaseCommand):
    help = "Управление сервером Daphne (запуск)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--log-level',
            type=str,
            choices=[level.value for level in LogLevel],
            default=LogLevel.INFO.value,
            help='Уровень логирования (info, warning, error, none)'
        )
        
    def handle(self, *args, **options):
        log_level = LogLevel(options['log_level'])
        daphne = Daphne()
        process = daphne.start_daphne(log_level)

        is_process_running = daphne.is_process_running(process)

        if is_process_running:
            print('Сервер запущен.')
        else:
            print('Сервер не запущен.')