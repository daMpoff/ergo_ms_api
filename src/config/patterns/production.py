from src.config.patterns.local import *

from src.config.env import env

SECRET_KEY = env.str('API_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = env.list('API_ALLOWED_HOSTS', default=[])