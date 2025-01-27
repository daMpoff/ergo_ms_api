"""
Файл содержащий конфигурацию базы данных для Django-приложения.
Он включает настройки для подключения к базе данных PostgreSQL и обработку ошибок подключения.
"""

import psycopg2

from django.core.exceptions import ImproperlyConfigured

from src.config.env import env

try:
    """
    Конфигурация базы данных для Django-приложения.
    Используется PostgreSQL в качестве базы данных.
    """
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('DB_NAME'),
            'USER': env.str('DB_USER'),
            'PASSWORD': env.str('DB_PASSWORD'),
            'HOST': env.str('DB_HOST'),
            'PORT': env.str('DB_PORT'),
        }
    }

    # Получаем конфигурацию базы данных по умолчанию.
    default_db = DATABASES['default']

    # Устанавливаем соединение с базой данных PostgreSQL.
    connection = psycopg2.connect(
        dbname=default_db['NAME'],
        user=default_db['USER'],
        password=default_db['PASSWORD'],
        host=default_db['HOST'],
        port=default_db['PORT']
    )

    cursor = connection.cursor()

    cursor.close()
    connection.close()
except (psycopg2.OperationalError, ImproperlyConfigured):
    """
    В случае ошибки подключения к базе данных или неправильной конфигурации,
    устанавливаем пустую конфигурацию базы данных.
    """
    DATABASES = {
        'default': {
        }
    }

"""
Настройка поля автоинкремента по умолчанию для моделей Django.
Используется BigAutoField для автоматического создания больших целочисленных полей.
"""
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Конфиг для работы с БД
class DBConfig:
    def __init__(self) -> None:
        self.USERNAME = DATABASES['default']['USER']
        self.PASSWORD = DATABASES['default']['PASSWORD']
        self.HOST = DATABASES['default']['HOST']
        self.PORT = DATABASES['default']['PORT']
        self.DB_NAME = DATABASES['default']['NAME']

    def __repr__(self) -> str:
        return self.SQLALCHEMY_URL

    @property
    def SQLALCHEMY_URL(self):
        return f"postgresql+psycopg2://{self.USERNAME}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB_NAME}"

    @property
    def POSTGRESQL_URL(self):
        return f"postgresql://{self.USERNAME}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB_NAME}"