from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.core.utils.server.redis import Redis

class Command(BaseCommand):
    help = 'Остановка Redis сервера'

    def handle(self, *args, **options):
        redis_path = getattr(settings, 'REDIS_PATH', None)
        if not redis_path:
            raise CommandError('REDIS_PATH не настроен в настройках')

        redis = Redis(redis_path=redis_path)
        success, message = redis.stop()

        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            raise CommandError(message)