from src.config.env import env

# Имя процесса сервера
SERVER_PROCESS_NAME = 'daphne.exe'

# Хост и порт из env файла
SERVER_HOST = env.str('API_HOST') or 'localhost'
SERVER_PORT = env.str('API_PORT') or '8000'