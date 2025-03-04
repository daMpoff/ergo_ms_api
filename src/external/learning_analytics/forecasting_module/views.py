from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.core.utils.methods import parse_errors_to_dict
from src.core.utils.base.base_views import BaseAPIView
from src.core.utils.database.main import OrderedDictQueryExecutor
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from src.external.learning_analytics.forecasting_module.models import(
    Speciality
)

from src.external.learning_analytics.forecasting_module.serializers import(
    SpecialitySerializer
)

from src.external.learning_analytics.forecasting_module.scripts import(
    get_specialities,
    get_all_specialities
)

# Представление данных для получения информации о специальностях
class SpecialityGetView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о направлениях подготовки. Если указан параметр 'id', возвращается конкретное направление. Если параметр 'id' не указан, возвращаются все направления",
        manual_parameters=[
            openapi.Parameter(
                'id', # Имя параметра
                openapi.IN_QUERY, # Параметр передается в query-строке
                type = openapi.TYPE_INTEGER, # Тип параметра (целочисленный)
                required=False,
                description="Идентификатор направления подготовки (опционально)", # Описание параметра
            )
        ],
        responses={
            200: "Информация о направлениях подготовки", # Успешный ответ
            400: "Ошибка" # Ошибка
        }
    )
    def get(self, request):
        """
        Обработка GET-запроса для получения информации о направлениях подготовки.
        В случае передачи параметра 'id', возвращает данные о направлениях подготовки.
        Если параметр 'id' не передан - возвращаются все данные о направлениях подготовки.
        """
        speciality_id = request.query_params.get('id') # Получаем параметр 'id' из query-строки

        if speciality_id:
            # Если передан 'id', получаем данные о конкретной специальности
            speciality = OrderedDictQueryExecutor.fetchall(
                get_specialities, speciality_id = speciality_id
            )
            if not speciality:
                # Если специальность не обнаружена - возвращаем ошибку 404
                return Response(
                    {"message": "Направление подготовки (специальность) с указанным ID не найдена"},
                    status = status.HTTP_404_NOT_FOUND
                )
            # Формируем успешный ответ с данными о специальности
            response_data = {
                "data": speciality,
                "message": "Специальность получена успешно"
            }
        else:
            # Если 'id' не передан, получаем данные обо всех специальностях
            specialities = OrderedDictQueryExecutor.fetchall(get_all_specialities)
            # Формируем успешный ответ с данными обо всех специальностях
            response_data = {
                "data": specialities,
                "message": "Все специальности получены успешно"
            }

        # Возвращаем ответ с данными и статусом 200
        return Response(response_data, status=status.HTTP_200_OK)

class SendSpecialityView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Проверка ввода специальности",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,  # Тип тела запроса (объект JSON)
            properties={
                'code': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Код специальности'  # Описание поля
                ),
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Наименование специальности'  # Описание поля
                ),
                'specialization': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Специализация'  # Описание поля
                ),
                'department': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Кафедра'  # Описание поля
                ),
                'faculty': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Факультет'  # Описание поля
                ),
                'education_duration': openapi.Schema(
                    type=openapi.TYPE_INTEGER,  # Тип поля (целое число)
                    description='Срок получения образования (в месяцах)'  # Описание поля
                ),
                'year_of_admission': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (целое число)
                    description='Год поступления'  # Описание поля
                ),
            },
            required=['code', 'name', 'specialization', 'department', 'faculty', 'education_duration', 'year_of_admission'],  # Обязательные поля
            example={
                "code": "10.05.04",
                "name": "Информационно-аналитические системы безопасности",
                "specialization": "Автоматизация информационно-аналитической деятельности",
                "department": "Компьютерные технологии и системы",
                "faculty": "Факультет информационных технологий",
                "education_duration": 66,  # 5 лет и 6 месяцев = 66 месяцев
                "year_of_admission": "2021"
            }
        ),
        responses={
            201: "Специальность успешно сохранена",  # Успешный ответ
            400: "Произошла ошибка"  # Ошибка
        },
    )
    def post(self, request):
        """
        Обрабатывает POST-запрос для создания новой специальности.
        Проверяет валидность данных и сохраняет специальность в базе данных.
        """
        serializer = SpecialitySerializer(data=request.data)  # Создаем сериализатор с данными из запроса

        if serializer.is_valid():
            # Если данные валидны, сохраняем специальность
            serializer.save()
            # Возвращаем успешный ответ
            successful_response = Response(
                {"message": "Специальность сохранена успешно"},
                status=status.HTTP_200_OK
            )
            return successful_response

        # Если данные не валидны, преобразуем ошибки в словарь и возвращаем ошибку 400
        errors = parse_errors_to_dict(serializer.errors)
        return Response(
            errors,
            status=status.HTTP_400_BAD_REQUEST
        )
