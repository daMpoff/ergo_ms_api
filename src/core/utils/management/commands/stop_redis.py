"""
Файл для определения команды Django для остановки Redis сервера.

Этот файл содержит класс Command, который наследуется от BaseCommand и предоставляет 
функциональность для остановки запущенного процесса Redis сервера.

Пример использования:
>>> python src/manage.py stop_redis
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.core.utils.server.redis import Redis

logger = logging.getLogger('core.utils.commands')

class Command(BaseCommand):
    """
    Команда Django для остановки Redis сервера.
    
    Находит и останавливает запущенный процесс Redis сервера используя
    путь к исполняемому файлу из настроек Django.
    """
    help = 'Остановка Redis сервера'

    def handle(self, *args: tuple, **options: dict) -> None:
        """
        Выполняет команду остановки Redis сервера.

        Args:
            *args: Позиционные аргументы
            **options: Именованные аргументы

        Raises:
            CommandError: Если REDIS_PATH не настроен или возникла ошибка при остановке
        """
        logger.info('Запуск команды stop_redis')
        
        redis_path = getattr(settings, 'REDIS_PATH', None)
        if not redis_path:
            msg = 'REDIS_PATH не настроен в настройках'
            logger.error(msg)
            raise CommandError(msg)

        redis = Redis(redis_path=redis_path)
        logger.info('Остановка Redis сервера')
        success, message = redis.stop()

        if success:
            logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))
        else:
            logger.error(message)
            raise CommandError(message)