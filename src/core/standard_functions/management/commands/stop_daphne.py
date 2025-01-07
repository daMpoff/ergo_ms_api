from src.core.standard_functions.daphne import Daphne

from django.core.management.base import BaseCommand

from django.conf import settings

class Command(BaseCommand):
    help = "Управление сервером Daphne (остановка)"

    def handle(self, *args, **options):
        server_process_name = getattr(settings, 'SERVER_PROCESS_NAME', None)

        daphne = Daphne()
        is_stopped = daphne.stop_process(server_process_name)

        if is_stopped:
            print('Сервер успешно остановлен.')
        else:
            print('Не удалось остановить сервер.')