"""
Файл для определения команды Django для остановки Celery worker.

Этот файл содержит класс Command, который наследуется от BaseCommand и предоставляет 
функциональность для поиска и остановки запущенного процесса Celery worker.

Пример использования:
>>> python src/manage.py celery_worker_stop
"""

import psutil
import logging

from typing import Optional

from django.core.management.base import BaseCommand

logger = logging.getLogger('core.utils.commands')

class Command(BaseCommand):
    """
    Команда Django для остановки Celery worker.
    
    Находит и останавливает запущенный процесс Celery worker используя psutil.
    Использует SIGTERM для корректного завершения процесса.
    """
    help = 'Останавливает Celery worker'

    def find_celery_worker(self) -> Optional[psutil.Process]:
        """
        Ищет запущенный процесс Celery worker.

        Returns:
            Optional[psutil.Process]: Объект процесса если worker запущен, иначе None
        """
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['cmdline'] and 
                    'celery' in proc.info['cmdline'] and 
                    'worker' in proc.info['cmdline']):
                    logger.debug(f'Найден процесс Celery worker: PID={proc.pid}')
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f'Ошибка при поиске процесса: {e}')
                continue
        logger.debug('Процесс Celery worker не найден')
        return None

    def handle(self, *args: tuple, **options: dict) -> None:
        """
        Выполняет команду остановки Celery worker.

        Args:
            *args: Позиционные аргументы
            **options: Именованные аргументы
        """
        logger.info('Запуск команды celery_worker_stop')
        process = self.find_celery_worker()
        
        if process:
            try:
                logger.info(f'Остановка Celery worker (PID: {process.pid})')
                process.terminate()
                process.wait(timeout=5)
                msg = f'Celery worker процесс (PID: {process.pid}) успешно остановлен'
                logger.info(msg)
                self.stdout.write(self.style.SUCCESS(msg))
            except Exception as e:
                msg = f'Ошибка при остановке Celery worker: {str(e)}'
                logger.error(msg)
                self.stdout.write(self.style.ERROR(msg))
        else:
            msg = 'Celery worker процесс не найден'
            logger.warning(msg)
            self.stdout.write(self.style.WARNING(msg))