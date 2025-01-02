import os

import psycopg2
from psycopg2 import OperationalError

from dotenv import load_dotenv, find_dotenv

import time

import subprocess
import psutil
import argparse

import ctypes

parser = argparse.ArgumentParser(description="Скрипт проверки подключения к БД.")

parser.add_argument('--host', type=str, help="Адрес сервера", default='127.0.0.1')
parser.add_argument('--port', type=str, help="Порт", default='5432')
parser.add_argument('--username', type=str, help="Имя пользователя", default='postgres')
parser.add_argument('--password', type=str, help="Пароль", default='admin')
parser.add_argument('--database', type=str, help="Название БД", default='oms')

args = parser.parse_args()

def check_database_connection(host, port, username, password, database):
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            dbname=database
        )
        connection.close()
        print("Подключение успешно.")
        return True
    except OperationalError as e:
        print(f"Ошибка подключения: {e}")
        return False
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        return False

def create_env_file(host, port, username, password, database):
    env_path = find_dotenv('.env', raise_error_if_not_found=False)
    if os.path.exists(env_path):
        os.remove(env_path)

    with open('.env', 'w') as env_file:
        env_file.write(f"DB_NAME={database}\n")
        env_file.write(f"DB_USER={username}\n")
        env_file.write(f"DB_PASSWORD={password}\n")
        env_file.write(f"DB_HOST={host}\n")
        env_file.write(f"DB_PORT={port}\n")

    print(".env файл успешно создан.")

def find_process(name):
    """Find a process by name."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if name in proc.info['name'] or (proc.info['cmdline'] and any(name in arg for arg in proc.info['cmdline'])):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def stop_process(process):
    """Stop a process."""
    process.terminate()
    process.wait()

def start_daphne():
    """Start Daphne server."""
    process = subprocess.Popen(
        ['daphne', '-p', '8000', 'src.config.asgi:application'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return process

def main():
    a = ctypes.windll.shell32.IsUserAnAdmin()
    print(f"Админ: {a}\n")
    
    db_credentials = dict(args._get_kwargs())

    if check_database_connection(**db_credentials):
        create_env_file(**db_credentials)

        daphne_process = find_process('daphne')

        if daphne_process:
            print(f"Found Daphne process with PID {daphne_process.pid}. Stopping it...")
            stop_process(daphne_process)
            print("Daphne process stopped.")

        d = start_daphne()

        #stop_process(d)

        print("Daphne server is running.")
    else:
        print("Failed to connect to the database. Exiting.")

if __name__ == "__main__":
    main()