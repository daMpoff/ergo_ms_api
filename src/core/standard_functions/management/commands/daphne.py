import subprocess
import psutil

class Daphne:
    def find_process(self, process_name) -> psutil.Process:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if process_name in proc.info['name'] or (proc.info['cmdline'] and any(process_name in arg for arg in proc.info['cmdline'])):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                print(f'{e}')

        return None

    def __stop_process(self, process) -> bool:
        try:
            process.terminate()
            process.wait(timeout=5)
            return True
        except Exception as e:
            print(f"Ошибка при остановке процесса: {e}")
            return False

    def stop_process(self, process_name) -> bool:
        daphne_process = self.find_process(process_name)

        if daphne_process:
            self.__stop_process(daphne_process)
            return True
        
        return False

    def start_daphne(self) -> psutil.Process:
        process = subprocess.Popen(
            ['daphne.exe', '-p', '8000', 'src.config.asgi:application'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
                
        return process
    
    def is_process_running(self, process: subprocess.Popen) -> bool:
        try:
            psutil_process = psutil.Process(process.pid)
            return psutil_process.is_running() and psutil_process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False