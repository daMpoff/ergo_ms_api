from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = 'Запускает Celery worker с настройками eventlet'

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
            'worker',
            f'--loglevel={options["loglevel"]}',
            '--pool=threads',
        ]
        
        try:
            self.stdout.write(
                self.style.SUCCESS('Запуск Celery worker...')
            )
            subprocess.run(cmd)
        except KeyboardInterrupt:
            sys.exit(0) 