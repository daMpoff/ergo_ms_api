from src.config.env import env

SERVER_PROCESS_NAME = 'daphne.exe'

SERVER_HOST = env.str('API_HOST') or 'localhost'
SERVER_PORT = env.str('API_PORT') or '8000'