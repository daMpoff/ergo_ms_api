import os
import sys
import subprocess

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

from src.core.standard_functions.serializers import ScriptSerializer

class CheckAPIView(APIView):
    @swagger_auto_schema(
        operation_description="Проверка.",

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
        data = request.data

        host = data.get('host')
        port = data.get('port')
        username = data.get('username')
        password = data.get('password')
        database = data.get('database')

        if not all([host, port, username, password, database]):
            return Response(
                {"message": "Отсутствует один или несколько из требуемых параметров: адрес сервера, username, password, or database"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            connection = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                dbname=database
            )
            connection.close()

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
            
            # после создания .env файла необходимо обязательно
            # обновить settings для того чтобы не перезапускать 
            # django сервер
            settings.DATABASES['default'].update({
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': database,
                'USER': username,
                'PASSWORD': password,
                'HOST': host,
                'PORT': port,
            })

            # если не выключить stdout и stderr, то при запуске
            # django из консоли, не работает команда migrate
            with open(os.devnull, 'w') as fnull:
                sys.stdout = fnull
                sys.stderr = fnull

                call_command('migrate')

            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            return Response({"message": "Подключение успешно."}, status=status.HTTP_200_OK)
        except OperationalError as e:
            return Response({"message": "Нет подключения к базе данных."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExecuteScriptView(APIView):
    @swagger_auto_schema(
        request_body=ScriptSerializer,
        responses={
            200: openapi.Response('Success', ScriptSerializer),
            400: 'Bad Request'
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = ScriptSerializer(data=request.data)
        if serializer.is_valid():
            language = serializer.validated_data['language']
            code = serializer.validated_data['code']

            script_file = f'script.{language}'
            current_directory = os.getcwd()
            dir = os.path.join(current_directory, script_file)

            print(os.path.exists(dir))  
            print(dir)
            
            if language == 'py':
                result = subprocess.run(['python', script_file], capture_output=True, text=True)
            elif language == 'js':
                result = subprocess.run(['node', script_file], capture_output=True, text=True)
            elif language == 'cs':
                os.environ["PATH"] += os.pathsep + r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319"
                subprocess.run(["csc", script_file])
                result = subprocess.run(["script.exe"], capture_output=True, text=True)
            elif language == 'cpp':
                subprocess.run(["g++", script_file], check=True)
                result = subprocess.run(["script.exe"], text=True, capture_output=True)
            elif language == 'php':
                result = subprocess.run(['php', script_file], capture_output=True, text=True, encoding='utf-8')
            elif language == 'rb':
                result = subprocess.run(['ruby', script_file], capture_output=True, text=True)
            else:
                return Response({'error': 'Unsupported language'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'output': result.stdout, 'error': result.stderr}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)