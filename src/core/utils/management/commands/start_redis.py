"""
Файл для определения команды Django для запуска Redis сервера.

Этот файл содержит класс Command, который наследуется от BaseCommand и предоставляет 
функциональность для запуска Redis сервера с опциональной конфигурацией.

Пример использования:
>>> python src/manage.py start_redis [--config=path/to/config.conf]
"""

import logging

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.conf import settings

from src.core.utils.server.redis import Redis

logger = logging.getLogger('core.utils.commands')

class Command(BaseCommand):
    """
    Команда Django для запуска Redis сервера.
    
    Запускает Redis сервер используя путь из настроек Django и
    опциональный конфигурационный файл.
    """
    help = 'Запуск Redis сервера используя настроенный путь к Redis'
    poetry_command_name = 'start_redis'

    def add_arguments(self, parser: CommandParser) -> None:
        """
        Добавляет аргументы командной строки.

        Args:
            parser: Парсер аргументов командной строки
        """
        parser.add_argument(
            '--config',
            help='Путь к конфигурационному файлу Redis',
            default=None
        )

    def handle(self, *args: tuple, **options: dict) -> None:
        """
        Выполняет команду запуска Redis сервера.

        Args:
            *args: Позиционные аргументы
            **options: Именованные аргументы, включая config

        Raises:
            CommandError: Если REDIS_PATH не настроен или возникла ошибка при запуске
        """
        logger.info('Запуск команды start_redis')
        
        redis_path = getattr(settings, 'REDIS_PATH', None)
        if not redis_path:
            msg = 'REDIS_PATH не настроен в настройках'
            logger.error(msg)
            raise CommandError(msg)

        redis = Redis(redis_path=redis_path)
        logger.info(f'Запуск Redis сервера из {redis_path}')
        if options['config']:
            logger.info(f'Используется конфигурационный файл: {options["config"]}')
            
        success, message = redis.start(config_path=options['config'])

        if success:
            logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))
        else:
            logger.error(message)
            raise CommandError(message)