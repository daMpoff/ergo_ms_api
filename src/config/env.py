import environ
import os

from src.config.settings.base import BASE_DIR

ENV_DIR = os.path.join(BASE_DIR.parent.parent, '.env')

env = environ.Env()
environ.Env.read_env(ENV_DIR)