from django.core.management.base import BaseCommand

from src.core.standard_functions.management.commands.daphne import Daphne

class Command(BaseCommand):
    help = "Управление сервером Daphne (запуск)"

    def handle(self, *args, **options):
        daphne = Daphne()
        process = daphne.start_daphne()

        is_process_running = daphne.is_process_running(process)
        
        if is_process_running == True:
            print(f'Сервер запущен.')
        else:
            print(f'Сервер не запущен.')