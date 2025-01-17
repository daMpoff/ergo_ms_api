"""
Файл содержащий API-представления (views) для Django-приложения.
"""

import os
import sys

import psycopg2
from psycopg2 import OperationalError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.core.management import call_command
from django.db.utils import OperationalError
from django.conf import settings

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class CheckAPIView(APIView):
    """
    APIView для проверки подключения к базе данных и выполнения миграций.

    Методы:
        post(request, *args, **kwargs): Обрабатывает POST-запрос для проверки подключения к базе данных.
    """

    @swagger_auto_schema(
        operation_description="Проверка подключения к базе данных.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'host': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Хост'
                ),
                'port': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Порт'
                ),
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Имя пользователя'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description='Пароль'
                ),
                'database': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='База данных'
                ),
            },
            required=['host', 'port', 'username', 'password', 'database']
        ),
        responses={
            200: 'Подключение успешно.',
            400: 'Отсутствует один или несколько из требуемых параметров.',
            500: 'Нет подключения к базе данных.',
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Обрабатывает POST-запрос для проверки подключения к базе данных.

        Аргументы:
            request: Объект запроса, содержащий данные для подключения к базе данных.

        Возвращает:
            Response: Ответ с сообщением о результате подключения.
        """
        data = request.data

        host = data.get('host')
        port = data.get('port')
        username = data.get('username')
        password = data.get('password')
        database = data.get('database')

        # Проверка наличия всех необходимых параметров
        if not all([host, port, username, password, database]):
            return Response(
                {"message": "Отсутствует один или несколько из требуемых параметров: адрес сервера, username, password, or database"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Попытка подключения к базе данных
            connection = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                dbname=database
            )
            connection.close()

            # Создание .env файла с параметрами подключения
            env_file_path = os.path.join(os.getcwd(), ".env")
            env_content = (
                f"DB_NAME={database}\n"
                f"DB_USER={username}\n"
                f"DB_PASSWORD={password}\n"
                f"DB_HOST={host}\n"
                f"DB_PORT={port}\n"
            )
            with open(env_file_path, "w") as env_file:
                env_file.write(env_content)

            # Обновление настроек базы данных в Django
            settings.DATABASES['default'].update({
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': database,
                'USER': username,
                'PASSWORD': password,
                'HOST': host,
                'PORT': port,
            })

            # Выполнение миграций без вывода в консоль
            with open(os.devnull, 'w') as fnull:
                sys.stdout = fnull
                sys.stderr = fnull
                call_command('migrate')

            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            return Response({"message": "Подключение успешно."}, status=status.HTTP_200_OK)
        except OperationalError as e:
            return Response({"message": "Нет подключения к базе данных."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)