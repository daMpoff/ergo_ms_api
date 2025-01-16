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