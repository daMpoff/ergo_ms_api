from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = 'Запускает Celery beat scheduler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            default='info',
            help='Уровень логирования (default: info)'
        )

    def handle(self, *args, **options):
        cmd = [
            'celery',
            '-A',
            'src',
            'beat',
            f'--loglevel={options["loglevel"]}'
        ]
        
        try:
            self.stdout.write(
                self.style.SUCCESS('Запуск Celery beat...')
            )
            subprocess.run(cmd)
        except KeyboardInterrupt:
            sys.exit(0) 