from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status, viewsets
from src.external.learning_analytics.models import (
    Employer
)
from src.external.learning_analytics.serializers import (
    EmployerSerializer
)
from src.core.utils.methods import parse_errors_to_dict
from src.core.utils.base.base_views import BaseAPIView
from src.external.learning_analytics.scripts import (
    get_employers
)

from src.external.learning_analytics.methods import (
    get_tables_info, 
    handle_db_errors,
    get_table_info,
    check_table_exists,
    clear_analytics_tables
)

from src.core.utils.database.main import OrderedDictQueryExecutor
from drf_yasg.utils import swagger_auto_schema # type: ignore
from drf_yasg import openapi # type: ignore
from django.db import connection
from django.core.cache import cache
from django.db.models import Count
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def handle_db_errors(func):
    """Декоратор для обработки ошибок БД"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper

class EmployerView(viewsets.ViewSet):
    @swagger_auto_schema(
        operation_description="Получение информации о всех работодателях",
        responses={200: "Информация о работодателях"}
    )
    def list(self, request):
        employers = OrderedDictQueryExecutor.fetchall(get_employers)
        response_data = {"data": employers, "message": "Все работодатели получены успешно"}
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Создание одного или нескольких работодателей",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'company_name': openapi.Schema(type=openapi.TYPE_STRING, description='Название компании'),
                    'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание компании'),
                    'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description='Контактный email компании'),
                    'rating': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_DECIMAL, description='Рейтинг компании от 0 до 5'),
                },
                required=['company_name', 'description', 'email', 'rating'],
                example={
                    "company_name": "Tech Innovations Inc.",
                    "description": "Компания, специализирующаяся на разработке инновационных технологий в области искусственного интеллекта и машинного обучения.",
                    "email": "info@techinnovations.com",
                    "rating": 4.75
                }
            )
        ),
        responses={201: "Работодатель(и) успешно созданы", 400: "Ошибка валидации данных"},
    )
    def create(self, request):
        data = request.data
        is_many = isinstance(data, list)
        if not is_many:
            data = [data]
        existing = set(
            Employer.objects.filter(
                company_name__in=[item.get('company_name') for item in data],
                email__in=[item.get('email') for item in data]
            ).values_list('company_name', 'email')
        )
        to_create = [item for item in data if (item.get('company_name'), item.get('email')) not in existing]
        skipped = [item for item in data if (item.get('company_name'), item.get('email')) in existing]
        if not to_create:
            return Response({
                "added": [],
                "skipped": skipped,
                "message": "Все объекты уже существуют в базе, ничего не добавлено"
            }, status=status.HTTP_200_OK)
        serializer = EmployerSerializer(data=to_create, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "added": serializer.data,
                "skipped": skipped,
                "message": f"Добавлено: {len(serializer.data)}, пропущено (дубликаты): {len(skipped)}"
            }, status=status.HTTP_201_CREATED)
        errors = serializer.errors
        if isinstance(errors, list):
            errors = {str(i): err for i, err in enumerate(errors)}
        return Response(parse_errors_to_dict(errors), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Получение информации о работодателе по id",
        responses={200: "Информация о работодателе", 404: "Работодатель не найден"}
    )
    def retrieve(self, request, pk=None):
        employer = OrderedDictQueryExecutor.fetchall(get_employers, employer_id=pk)
        if not employer:
            return Response({"message": "Работодатель с указанным ID не найден"}, status=status.HTTP_404_NOT_FOUND)
        response_data = {"data": employer, "message": "Компетенция получена успешно"}
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Обновление информации о работодателе",
        request_body=EmployerSerializer,
        responses={200: "Информация о работодателе обновлена успешно", 400: "Ошибка валидации данных", 404: "Работодатель не найден"}
    )
    def update(self, request, pk=None):
        try:
            employer = Employer.objects.get(id=pk)
        except Employer.DoesNotExist:
            return Response({"message": "Работодатель с указанным ID не найден"}, status=status.HTTP_404_NOT_FOUND)
        serializer = EmployerSerializer(employer, data=request.data, partial=False)
        if not serializer.is_valid():
            return Response({"message": "Ошибка валидации данных", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        updated_employer = OrderedDictQueryExecutor.fetchall(get_employers, employer_id=pk)
        response_data = {"data": updated_employer, "message": "Информация о работодателе обновлена успешно"}
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Удаление работодателя по идентификатору",
        responses={204: "Работодатель успешно удален", 404: "Работодатель не найден"}
    )
    def destroy(self, request, pk=None):
        try:
            employer = Employer.objects.get(id=pk)
        except Employer.DoesNotExist:
            return Response({"message": "Работодатель с указанным ID не найден"}, status=status.HTTP_404_NOT_FOUND)
        employer.delete()
        return Response({"message": "Работодатель успешно удален"}, status=status.HTTP_204_NO_CONTENT)

class DatabaseTablesView(APIView):
    CACHE_TIMEOUT = 60 * 5  # 5 минут

    @swagger_auto_schema(
        operation_description="Получение списка таблиц базы данных или данных конкретной таблицы",
        manual_parameters=[
            openapi.Parameter(
                'table',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Имя таблицы (опционально)"
            )
        ],
        responses={
            200: "Успешное получение данных",
            400: "Неверное имя таблицы",
            500: "Ошибка базы данных"
        }
    )
    @handle_db_errors
    def get(self, request):
        table_name = request.query_params.get('table')

        if table_name:
            cache_key = f'table_data_{table_name}'
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data)

        try:
            with connection.cursor() as cursor:
                if table_name:
                    if not check_table_exists(cursor, table_name):
                        return Response(
                            {'error': 'Table not found'},
                            status=status.HTTP_404_NOT_FOUND
                        )

                    columns_info = get_table_info(cursor, table_name)
                    
                    cursor.execute(f'SELECT * FROM "{table_name}"')
                    rows = cursor.fetchall()
                    
                    columns = [
                        {
                            'name': col[0],
                            'type': col[1],
                            'nullable': col[2] == 'YES'
                        } for col in columns_info
                    ]
                    
                    formatted_rows = [
                        dict(zip([col['name'] for col in columns], row))
                        for row in rows
                    ]

                    response_data = {
                        'table_name': table_name,
                        'columns': columns,
                        'rows': formatted_rows
                    }
                    cache.set(cache_key, response_data, self.CACHE_TIMEOUT)
                    return Response(response_data)
                else:
                    tables_data = get_tables_info(cursor)
                    return Response({'tables': tables_data})
        except Exception as e:
            logger.error(f"Error fetching table data: {str(e)}")
            raise

class ClearTablesView(APIView):
    @swagger_auto_schema(
        operation_description="Очистка всех таблиц аналитического модуля",
        responses={
            200: "Таблицы успешно очищены",
            500: "Ошибка при очистке таблиц"
        }
    )
    @handle_db_errors
    def post(self, request):
        try:
            import time
            start_time = time.time()
            
            with connection.cursor() as cursor:
                # Выполняем очистку таблиц
                result = clear_analytics_tables(cursor)
                
                elapsed_time = time.time() - start_time
                
                # Форматируем сообщение о результатах
                logger.info(f"Результаты очистки: очищено таблиц: {len(result.get('cleared_tables', []))}, "
                           f"сброшено последовательностей: {len(result.get('reset_sequences', []))}")
                
                return Response(
                    {
                        "message": "Все таблицы успешно очищены",
                        "execution_time": f"{elapsed_time:.2f} секунд",
                        "result": result
                    },
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            logger.error(f"Ошибка при очистке таблиц: {str(e)}")
            return Response(
                {
                    "error": f"Произошла ошибка при очистке таблиц: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoadSampleEmployerData(APIView):
    def post(self, request):
        try:
            import json
            import os
            from django.conf import settings
            from src.external.learning_analytics.models import Employer

            json_path = os.path.join(settings.BASE_DIR, 'external', 'learning_analytics', 'data', 'sample_employers.json')
            with open(json_path, encoding='utf-8') as f:
                employers_data = json.load(f).get('employers', [])

            created = []
            skipped = []
            for item in employers_data:
                obj, is_created = Employer.objects.get_or_create(
                    company_name=item['company_name'],
                    email=item['email'],
                    defaults={
                        'description': item.get('description', ''),
                        'rating': item.get('rating', 0)
                    }
                )
                if is_created:
                    created.append(obj.company_name)
                else:
                    skipped.append(item)
            return Response({'message': f'Загружено {len(created)} работодателей', 'added': created, 'skipped': skipped}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


