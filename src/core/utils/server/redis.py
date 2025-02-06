"""
Файл для управления Redis сервером.

Этот файл содержит класс Redis, который предоставляет функциональность для:
- Запуска Redis сервера с опциональной конфигурацией
- Остановки Redis сервера
- Проверки статуса работы сервера

Пример использования:
>>> from src.core.utils.server.redis import Redis
>>> redis = Redis('/path/to/redis')
>>> success, msg = redis.start(config_path='redis.conf')
>>> success, msg = redis.stop()
>>> is_running = redis.is_running()
"""

import os
import subprocess
import psutil
import logging

from typing import Optional, Tuple

logger = logging.getLogger('core.utils.server')

class Redis:
    """
    Класс для управления Redis сервером.

    Предоставляет методы для запуска и остановки Redis сервера,
    а также проверки его статуса.

    Args:
        redis_path: Путь к исполняемому файлу Redis
    """
    
    def __init__(self, redis_path: str):
        """
        Инициализация объекта Redis.

        Args:
            redis_path: Путь к исполняемому файлу Redis
        """
        self.redis_path = os.getcwd() + redis_path
        self.process: Optional[subprocess.Popen] = None
    
    def start(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Запуск Redis сервера.
        
        Args:
            config_path: Путь к конфигурационному файлу Redis
            
        Returns:
            Tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            if self.is_running():
                return False, "Redis сервер уже запущен"

            if not os.path.exists(self.redis_path):
                return False, f"Исполняемый файл Redis не найден по пути: {self.redis_path}"

            command = [self.redis_path]
            
            if config_path:
                if not os.path.exists(config_path):
                    return False, f"Конфигурационный файл не найден по пути: {config_path}"
                command.extend(['--config', config_path])

            logger.info(f'Запуск Redis сервера с командой: {" ".join(command)}')
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Проверяем успешность запуска
            try:
                self.process.wait(timeout=5)
                stderr = self.process.stderr.read()
                logger.error(f'Ошибка при запуске Redis: {stderr}')
                return False, f"Не удалось запустить Redis: {stderr}"
            except subprocess.TimeoutExpired:
                logger.info('Redis сервер успешно запущен')
                return True, "Redis сервер успешно запущен"

        except Exception as e:
            logger.error(f'Ошибка при запуске Redis: {e}')
            return False, f"Ошибка при запуске Redis: {str(e)}"

    def stop(self) -> Tuple[bool, str]:
        """
        Остановка Redis сервера.
        
        Returns:
            Tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            if not self.is_running():
                return False, "Redis сервер не запущен"

            logger.info('Остановка Redis сервера')
            # Находим все процессы Redis
            for proc in psutil.process_iter(['name']):
                if 'redis' in proc.info['name'].lower():
                    proc.kill()
                    logger.info(f'Процесс Redis PID={proc.pid} остановлен')

            logger.info('Redis сервер успешно остановлен')
            return True, "Redis сервер успешно остановлен"

        except Exception as e:
            logger.error(f'Ошибка при остановке Redis: {e}')
            return False, f"Ошибка при остановке Redis: {str(e)}"

    def is_running(self) -> bool:
        """
        Проверка, запущен ли Redis сервер.
        
        Returns:
            bool: True если сервер запущен, иначе False
        """
        for proc in psutil.process_iter(['name']):
            try:
                if 'redis' in proc.info['name'].lower():
                    logger.debug(f'Найден процесс Redis: PID={proc.pid}')
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        logger.debug('Процесс Redis не найден')
        return False

    def restart(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Перезапуск Redis сервера.
        
        Args:
            config_path: Путь к конфигурационному файлу Redis
            
        Returns:
            Tuple[bool, str]: (успех операции, сообщение)
        """
        logger.info('Перезапуск Redis сервера')
        stop_success, stop_message = self.stop()
        if not stop_success:
            return False, stop_message
            
        return self.start(config_path)