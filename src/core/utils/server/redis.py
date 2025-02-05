import os
import subprocess
import psutil
from typing import Optional, Tuple

class Redis:
    """Класс для управления Redis сервером"""
    
    def __init__(self, redis_path: str):
        self.redis_path = os.getcwd() + redis_path
        self.process: Optional[subprocess.Popen] = None
    
    def start(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Запуск Redis сервера
        
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
                return False, f"Не удалось запустить Redis: {stderr}"
            except subprocess.TimeoutExpired:
                return True, "Redis сервер успешно запущен"

        except Exception as e:
            return False, f"Ошибка при запуске Redis: {str(e)}"

    def stop(self) -> Tuple[bool, str]:
        """
        Остановка Redis сервера
        
        Returns:
            Tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            if not self.is_running():
                return False, "Redis сервер не запущен"

            # Находим все процессы Redis
            for proc in psutil.process_iter(['name']):
                if 'redis' in proc.info['name'].lower():
                    proc.kill()

            return True, "Redis сервер успешно остановлен"

        except Exception as e:
            return False, f"Ошибка при остановке Redis: {str(e)}"

    def is_running(self) -> bool:
        """
        Проверка, запущен ли Redis сервер
        
        Returns:
            bool: True если сервер запущен, иначе False
        """
        for proc in psutil.process_iter(['name']):
            try:
                if 'redis' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def restart(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Перезапуск Redis сервера
        
        Args:
            config_path: Путь к конфигурационному файлу Redis
            
        Returns:
            Tuple[bool, str]: (успех операции, сообщение)
        """
        stop_success, stop_message = self.stop()
        if not stop_success:
            return False, stop_message
            
        return self.start(config_path)