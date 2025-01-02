import psycopg2

from django.core.exceptions import ImproperlyConfigured

from src.config.env import env

try:
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

    default_db = DATABASES['default']

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
    DATABASES = {
        'default': {
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'