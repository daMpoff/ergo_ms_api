from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.core.utils.server.redis import Redis

class Command(BaseCommand):
    help = 'Запуск Redis сервера используя настроенный путь к Redis'
    poetry_command_name = 'start_redis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            help='Путь к конфигурационному файлу Redis',
            default=None
        )

    def handle(self, *args, **options):
        redis_path = getattr(settings, 'REDIS_PATH', None)
        if not redis_path:
            raise CommandError('REDIS_PATH не настроен в настройках')

        redis = Redis(redis_path=redis_path)
        success, message = redis.start(config_path=options['config'])

        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            raise CommandError(message)