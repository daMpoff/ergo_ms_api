"""
Файл для управления процессом Daphne сервера.

Этот файл содержит класс Daphne, который предоставляет функциональность для:
- Поиска процессов по имени
- Запуска Daphne сервера
- Остановки процессов
- Проверки статуса работы процесса

Класс обеспечивает управление жизненным циклом Daphne сервера и логирование его работы.
"""

import subprocess
import threading
import psutil

from django.conf import settings

from src.core.utils.enums import LogLevel

class Daphne:
    def find_process(self, process_name: str) -> psutil.Process:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (process_name in proc.info['name'] or 
                    (proc.info['cmdline'] and 
                    any(process_name in arg for arg in proc.info['cmdline']))):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                print(f'{e}')

        return None

    def __stop_process(self, process: psutil.Process) -> bool:
        try:
            process.terminate()
            process.wait(timeout=5)
            return True
        except Exception as e:
            print(f"Ошибка при остановке процесса: {e}")
            return False

    def stop_process(self, process_name: str) -> bool:
        daphne_process = self.find_process(process_name)

        if daphne_process:
            self.__stop_process(daphne_process)
            return True
        
        return False

    def start_daphne(self, log_level: LogLevel = LogLevel.INFO) -> psutil.Process:
        server_process_name = getattr(settings, 'SERVER_PROCESS_NAME', None)
        server_port = getattr(settings, 'SERVER_PORT', None)
        server_host = getattr(settings, 'SERVER_HOST', None)

        process = subprocess.Popen(
            [server_process_name, '-p', server_port, '-b', server_host, 'src.config.asgi:application'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Функция для чтения и вывода строк из потока
        def read_output(pipe, log_level: LogLevel):
            for line in iter(pipe.readline, ''):
                if log_level == LogLevel.ERROR and 'ERROR' in line:
                    print(line.strip())
                elif log_level == LogLevel.WARNING and 'WARNING' in line:
                    print(line.strip())
                elif log_level == LogLevel.INFO:
                    print(line.strip())
                elif log_level == LogLevel.NONE:
                    continue

        # Запуск функции для чтения stdout в отдельном потоке
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, log_level))
        stdout_thread.start()

        # Запуск функции для чтения stderr в отдельном потоке
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, log_level))
        stderr_thread.start()

        return process
    
    def is_process_running(self, process: subprocess.Popen) -> bool:
        try:
            psutil_process = psutil.Process(process.pid)
            return psutil_process.is_running() and psutil_process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False