from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from src.external.learning_analytics.models import (
    Technology,
    Competention,
    Employer
)
from src.external.learning_analytics.serializers import (
    TechnologySerializer,
    CompetentionSerializer,
    EmployerSerializer
)
from src.core.utils.methods import parse_errors_to_dict
from src.core.utils.base.base_views import BaseAPIView
from src.external.learning_analytics.scripts import (
    get_technologies,
    get_competentions,
    get_employers
)

from src.core.utils.database.main import OrderedDictQueryExecutor
from drf_yasg.utils import swagger_auto_schema # type: ignore
from drf_yasg import openapi # type: ignore

# Представление данных для удаления (DELETE) работодателей
class EmployerDeleteView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Удаление работодателя по идентификатору",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Идентификатор работодателя"
            )
        ],
        responses={
            204: "Работодатель успешно удален",  # Успешный ответ (без содержимого)
            400: "Идентификатор работодателя не указан",  # Ошибка
            404: "Работодатель не найден"  # Ошибка
        }
    )
    def delete(self, request):
        """
        Обработка DELETE-запроса для удаления работодателя.
        """
        employer_id = request.query_params.get('id')  # Получаем параметр 'id' из query-строки

        if not employer_id:
            return Response(
                {"message": "Идентификатор работодателя не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            employer = Employer.objects.get(id=employer_id)  # Ищем работодателя по ID
        except Employer.DoesNotExist:
            return Response(
                {"message": "Работодатель с указанным ID не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        employer.delete()  # Удаляем работодателя из базы данных

        return Response(
            {"message": "Работодатель успешно удален"},
            status=status.HTTP_204_NO_CONTENT
        )

# Представление данных для обновления (PUT) работодателей
class EmployerPutView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Обновление информации о работодателе",
        request_body=EmployerSerializer,
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Идентификатор работодателя"
            )
        ],
        responses={
            200: "Информация о работодателе обновлена успешно",
            400: "Ошибка валидации данных",
            404: "Работодатель не найден"
        }
    )
    def put(self, request):
        """
        Обновление информации о работодателе (обработка PUT-запроса).
        """
        employer_id = request.query_params.get('id')
        if not employer_id:
            return Response(
                {"message": "Идентификатор работодателя не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            employer = Employer.objects.get(id=employer_id)
        except Employer.DoesNotExist:
            return Response(
                {"message": "Работодатель с указанным ID не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EmployerSerializer(employer, data=request.data, partial=False)
        if not serializer.is_valid():
            return Response(
                {"message": "Ошибка валидации данных", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обновляем данные работодателя
        serializer.save()

        # Получаем обновленные данные
        updated_employer = OrderedDictQueryExecutor.fetchall(
            get_employers, employer_id=employer_id
        )

        response_data = {
            "data": updated_employer,
            "message": "Информация о работодателе обновлена успешно"
        }

        return Response(response_data, status=status.HTTP_200_OK)

# Представление данных для получения (GET) работодателей
class EmployerGetView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о работодателях. Если указан параметр 'id', возвращается конкретный работодатель. Если параметр 'id' не указан, возвращаются все работодатели",
        manual_parameters=[
            openapi.Parameter(
                'id', # Имя параметра
                openapi.IN_QUERY, # Параметр передается в query-строке
                type = openapi.TYPE_INTEGER, # Тип параметра (целочисленный)
                required=False,
                description="Идентификатор работодателя (опционально)", # Описание параметра
            )
        ],
        responses={
            200: "Информация о работодателях", # Успешный ответ
            400: "Ошибка" # Ошибка
        }
    )
    def get(self, request):
        """
        Обработка GET-запроса для получения информации о работодателях
        В случае передачи параметра 'id', возвращает данные о конкретном работодателе.
        Если параметр 'id' не передан - возвращаются все данные о работодателях.
        """
        employer_id = request.query_params.get('id') # Получаем параметр 'id' из query-строки

        if employer_id:
            # Если передан 'id', получаем данные о конкретном работодателе
            employer = OrderedDictQueryExecutor.fetchall(
                get_employers, employer_id = employer_id
            )
            if not employer:
                # Если работодатель не обнаружена - возвращаем ошибку 404
                return Response(
                    {"message": "Работодатель с указанным ID не найден"},
                    status = status.HTTP_404_NOT_FOUND
                )
            # Формируем успешный ответ с данными о работодателе
            response_data = {
                "data": employer,
                "message": "Компетенция получена успешно"
            }
        else:
            # Если 'id' не передан, получаем данные обо всех технологиях
            employers = OrderedDictQueryExecutor.fetchall(get_employers)
            # Формируем успешный ответ с данными обо всех технологиях
            response_data = {
                "data": employers,
                "message": "Все работодатели получены успешно"
            }

        # Возвращаем ответ с данными и статусом 200
        return Response(response_data, status=status.HTTP_200_OK)
    
# Представление данных для создания (POST) работодателей
class EmployerSendView(APIView):
    @swagger_auto_schema(
        operation_description="Создание нового работодателя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,  # Тип тела запроса (объект JSON)
            properties={
                'company_name': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Название компании',  # Описание поля
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Описание компании',  # Описание поля
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    format=openapi.FORMAT_EMAIL,  # Указываем формат email
                    description='Контактный email компании',  # Описание поля
                ),
                'rating': openapi.Schema(
                    type=openapi.TYPE_NUMBER,  # Тип поля (число)
                    format=openapi.FORMAT_DECIMAL,  # Указываем формат числа с плавающей точкой
                    description='Рейтинг компании от 0 до 5',  # Описание поля
                ),
            },
            required=['company_name', 'description', 'email', 'rating'],  # Обязательные поля
            example={
                "company_name": "Tech Innovations Inc.",
                "description": "Компания, специализирующаяся на разработке инновационных технологий в области искусственного интеллекта и машинного обучения.",
                "email": "info@techinnovations.com",
                "rating": 4.75
            }
        ),
        responses={
            201: "Работодатель успешно создан",  # Успешный ответ
            400: "Произошла ошибка"  # Ошибка
        },
    )
    def post(self, request):
        """
        Обрабатывает POST-запрос для создания нового работодателя.
        Проверяет валидность данных и сохраняет работодателя в базе данных.
        """
        serializer = EmployerSerializer(data=request.data)  # Создаем сериализатор с данными из запроса

        if serializer.is_valid():
            # Если данные валидны, сохраняем работодателя
            serializer.save()
            # Возвращаем успешный ответ
            return Response(
                {"message": "Работодатель успешно создан"},
                status=status.HTTP_201_CREATED
            )

        # Если данные не валидны, возвращаем ошибку 400
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

# Представление данных для удаления (DELETE) компетенций
class CompetentionDeleteView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Удаление компетенции по идентификатору",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Идентификатор компетенции"
            )
        ],
        responses={
            204: "Компетенция успешно удален",  # Успешный ответ (без содержимого)
            400: "Идентификатор компетенции не указан",  # Ошибка
            404: "Компетенция не найдена"  # Ошибка
        }
    )
    def delete(self, request):
        """
        Обработка DELETE-запроса для удаления компетенции.
        """
        competention_id = request.query_params.get('id')  # Получаем параметр 'id' из query-строки

        if not competention_id:
            return Response(
                {"message": "Идентификатор компетенции не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            competention = Competention.objects.get(id=competention_id)  # Ищем компетенцию по ID
        except Competention.DoesNotExist:
            return Response(
                {"message": "Компетенция с указанным ID не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        competention.delete()  # Удаляем компетенцию из базы данных

        return Response(
            {"message": "Компетенция успешно удалена"},
            status=status.HTTP_204_NO_CONTENT
        )

# Представление данных для обновления (PUT) компетенций
class CompetentionPutView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Обновление информации о компетенции",
        request_body=CompetentionSerializer,
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Идентификатор компетенции"
            )
        ],
        responses={
            200: "Информация о компетенции обновлена успешно",
            400: "Ошибка валидации данных",
            404: "Компетенция не найдена"
        }
    )
    def put(self, request):
        """
        Обновление информации о компетенции (обработка PUT-запроса).
        """
        competention_id = request.query_params.get('id')
        if not competention_id:
            return Response(
                {"message": "Идентификатор компетенции не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            competention = Competention.objects.get(id=competention_id)
        except Competention.DoesNotExist:
            return Response(
                {"message": "Компетенция с указанным ID не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CompetentionSerializer(competention, data=request.data, partial=False)
        if not serializer.is_valid():
            return Response(
                {"message": "Ошибка валидации данных", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обновляем данные работодателя
        serializer.save()

        # Получаем обновленные данные
        updated_competention = OrderedDictQueryExecutor.fetchall(
            get_competentions, competention_id=competention_id
        )

        response_data = {
            "data": updated_competention,
            "message": "Информация о компетенции обновлена успешно"
        }

        return Response(response_data, status=status.HTTP_200_OK)

# Представление данных для получения (GET) компетенций
class CompetentionGetView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о компетенциях. Если указан параметр 'id', возвращается конкретная компетенция. Если параметр 'id' не указан, возвращаются все компетенции",
        manual_parameters=[
            openapi.Parameter(
                'id', # Имя параметра
                openapi.IN_QUERY, # Параметр передается в query-строке
                type = openapi.TYPE_INTEGER, # Тип параметра (целочисленный)
                required=False,
                description="Идентификатор компетенции (опционально)", # Описание параметра
            )
        ],
        responses={
            200: "Информация о компетенциях", # Успешный ответ
            400: "Ошибка" # Ошибка
        }
    )
    def get(self, request):
        """
        Обработка GET-запроса для получения информации о компетенциях.
        В случае передачи параметра 'id', возвращает данные о конкретной компетенциях.
        Если параметр 'id' не передан - возвращаются все данные о компетенциях.
        """
        competention_id = request.query_params.get('id') # Получаем параметр 'id' из query-строки

        if competention_id:
            # Если передан 'id', получаем данные о конкретной технологии
            competention = OrderedDictQueryExecutor.fetchall(
                get_competentions, competention_id = competention_id
            )
            if not competention:
                # Если компетенция не обнаружена - возвращаем ошибку 404
                return Response(
                    {"message": "Компетенция с указанным ID не найдена"},
                    status = status.HTTP_404_NOT_FOUND
                )
            # Формируем успешный ответ с данными о технологии
            response_data = {
                "data": competentions,
                "message": "Компетенция получена успешно"
            }
        else:
            # Если 'id' не передан, получаем данные обо всех технологиях
            competentions = OrderedDictQueryExecutor.fetchall(get_competentions)
            # Формируем успешный ответ с данными обо всех технологиях
            response_data = {
                "data": competentions,
                "message": "Все технологии получены успешно"
            }

        # Возвращаем ответ с данными и статусом 200
        return Response(response_data, status=status.HTTP_200_OK)

# Представление данных для создания (POST) компетенций
class CompetentionSendView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Проверка ввода компетенции",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,  # Тип тела запроса (объект JSON)
            properties={
                'code': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (целое число)
                    description='Код'  # Описание поля
                ),
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Наименование'  # Описание поля
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,  # Тип поля (строка)
                    description='Описание'  # Описание поля
                ),
            },
            required=['code', 'name', 'description'],  # Обязательные поля
            example={
                "code": "ОПК-8",
                "name": "Способен применять методы научных исследований при разработке информационно-аналитических систем безопасности",
                "description": "В этом случае компетенции соответствуют умения применять методы алгоритмизации, языки и технологии программирования при решении задач профессиональной деятельности, программировать, отлаживать и тестировать прототипы программно-технических комплексов, пригодные для практического применения"
            }
        ),
        responses={
            201: "Компетенция успешно сохранена",  # Успешный ответ
            400: "Произошла ошибка"  # Ошибка
        },
    )
    def post(self, request):
        """
        Обрабатывает POST-запрос для создания новой компетенции.
        Проверяет валидность данных и сохраняет компетенцию в базе данных.
        """
        serializer = CompetentionSerializer(data=request.data)  # Создаем сериализатор с данными из запроса

        if serializer.is_valid():
            # Если данные валидны, сохраняем технологию
            serializer.save()
            # Возвращаем успешный ответ
            successful_response = Response(
                {"message": "Компетенция сохранена успешно"},
                status=status.HTTP_200_OK
            )
            return successful_response

        # Если данные не валидны, преобразуем ошибки в словарь и возвращаем ошибку 400
        errors = parse_errors_to_dict(serializer.errors)
        return Response(
            errors,
            status=status.HTTP_400_BAD_REQUEST
        ) 

#Представление данных для удаления (DELETE) технологий
class TechnologyDeleteView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Удаление технологии по идентификатору",
        manual_parameters=[
            openapi.Parameter(
                'id',   
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Идентификатор технологии"
            )
        ],
        responses={
            204: "Технология успешно удалена",  # Успешный ответ (без содержимого)
            400: "Идентификатор технологии не указан",  # Ошибка
            404: "Технология не найдена"  # Ошибка
        }
    )
    def delete(self, request):
        """
        Обработка DELETE-запроса для удаления технологии.
        """
        technology_id = request.query_params.get('id')  # Получаем параметр 'id' из query-строки

        if not technology_id:
            return Response(
                {"message": "Идентификатор технологии не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            technology = Technology.objects.get(id=technology_id)  # Ищем технологию по ID
        except Technology.DoesNotExist:
            return Response(
                {"message": "Технология с указанным ID не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        technology.delete()  # Удаляем технологию из базы данных

        return Response(
            {"message": "Технология успешно удалена"},
            status=status.HTTP_204_NO_CONTENT
        )

# Представление данных для обновления (PUT) технологий
class TechnologyPutView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Обновление информации о технологии",
        request_body=TechnologySerializer,
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Идентификатор технологии"
            )
        ],
        responses={
            200: "Информация о технологии обновлена успешно",
            400: "Ошибка валидации данных",
            404: "Технология не найдена"
        }
    )
    def put(self, request):
        """
        Обновление информации о технологии (обработка PUT-запроса).
        """
        technology_id = request.query_params.get('id')
        if not technology_id:
            return Response(
                {"message": "Идентификатор технологии не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            technology = Technology.objects.get(id=technology_id)
        except Technology.DoesNotExist:
            return Response(
                {"message": "Технология с указанным ID не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TechnologySerializer(technology, data=request.data, partial=False)
        if not serializer.is_valid():
            return Response(
                {"message": "Ошибка валидации данных", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обновляем данные работодателя
        serializer.save()

        # Получаем обновленные данные
        updated_technology = OrderedDictQueryExecutor.fetchall(
            get_technologies, technology_id=technology_id
        )

        response_data = {
            "data": updated_technology,
            "message": "Информация о технологии обновлена успешно"
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
# Представление данных для получения (GET) технологий 
class TechnologyGetView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о технологиях. Если указан параметр 'id', возвращается конкретная технология. Если параметр 'id' не указан, возвращаются все технологии.",
        manual_parameters=[
            openapi.Parameter(
                'id',  # Имя параметра
                openapi.IN_QUERY,  # Параметр передается в query-строке
                type=openapi.TYPE_INTEGER,  # Тип параметра (целочисленный)
                required=False,  # Параметр не обязательный
                description="Идентификатор технологии (опционально)",  # Описание параметра
            )
        ],
        responses={
            200: "Информация о технологиях",  # Успешный ответ
            400: "Ошибка"  # Ошибка
        }
    )
    def get(self, request):
        """
        Обрабатывает GET-запрос для получения информации о технологиях.
        Если передан параметр 'id', возвращает данные о конкретной технологии.
        Если параметр 'id' не передан, возвращает данные обо всех технологиях.
        """
        technology_id = request.query_params.get('id')  # Получаем параметр 'id' из query-строки

        if technology_id:
            # Если передан 'id', получаем данные о конкретной технологии
            technologies = OrderedDictQueryExecutor.fetchall(
                get_technologies, technology_id=technology_id
            )
            if not technologies:
                # Если технология не найдена, возвращаем ошибку 404
                return Response(
                    {"message": "Технология с указанным ID не найдена"},
                    status=status.HTTP_404_NOT_FOUND
                )
            # Формируем успешный ответ с данными о технологии
            response_data = {
                "data": technologies,
                "message": "Технология получена успешно"
            }
        else:
            # Если 'id' не передан, получаем данные обо всех технологиях
            technologies = OrderedDictQueryExecutor.fetchall(get_technologies)
            # Формируем успешный ответ с данными обо всех технологиях
            response_data = {
                "data": technologies,
                "message": "Все технологии получены успешно"
            }

        # Возвращаем ответ с данными и статусом 200
        return Response(response_data, status=status.HTTP_200_OK)

# Представление данных для создания (POST) технологий
class TechnologySendView(APIView):
    """
    Представление для создания одной или нескольких технологий.
    Поддерживает как одиночные объекты, так и массивы объектов.
    """
    @swagger_auto_schema(
        operation_description="Создание одной или нескольких технологий",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,  # Указываем, что это массив
            items=openapi.Schema(  # Описываем элементы массива
                type=openapi.TYPE_OBJECT,
                properties={
                    'name': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Название технологии'
                    ),
                    'description': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Описание технологии'
                    ),
                    'popularity': openapi.Schema(
                        type=openapi.TYPE_NUMBER,
                        description='Популярность технологии (вещественное число)'
                    ),
                    'rating': openapi.Schema(
                        type=openapi.TYPE_NUMBER,
                        description='Рейтинг технологии (вещественное число)'
                    ),
                },
                required=['name', 'description', 'popularity', 'rating'],  # Обязательные поля
                example={
                    "name": "Python",
                    "description": "Python — это высокоуровневый язык программирования общего назначения, который широко используется для разработки веб-приложений, анализа данных, искусственного интеллекта и др.",
                    "popularity": 95.83,
                    "rating": 4.95
                }
            ),
            example=[  # Пример массива объектов
                {
                    "name": "Python",
                    "description": "Python — это высокоуровневый язык программирования общего назначения, который широко используется для разработки веб-приложений, анализа данных, искусственного интеллекта и др.",
                    "popularity": 95.83,
                    "rating": 4.95
                },
                {
                    "name": "Django",
                    "description": "Django — это мощный веб-фреймворк для Python, который позволяет быстро создавать безопасные и масштабируемые веб-приложения.",
                    "popularity": 90.12,
                    "rating": 4.85
                }
            ]
        ),
        responses={
            201: openapi.Response(
                description="Технология/технологии успешно сохранены",
                examples={
                    "application/json": {
                        "message": "Технология/технологии сохранены успешно"
                    }
                }
            ),
            400: openapi.Response(
                description="Ошибка валидации",
                examples={
                    "application/json": {
                        "name": ["Это поле обязательно."],
                        "popularity": ["Это поле должно быть числом."]
                    }
                }
            )
        },
    )
    def post(self, request):
        """
        Обрабатывает POST-запрос для создания одной или нескольких технологий.
        Проверяет валидность данных и сохраняет технологии в базе данных.
        
        Пример запроса для одной технологии:
        {
            "name": "Python",
            "description": "Python — это высокоуровневый язык программирования общего назначения...",
            "popularity": 95.83,
            "rating": 4.95
        }

        Пример запроса для нескольких технологий:
        [
            {
                "name": "Python",
                "description": "Python — это высокоуровневый язык программирования общего назначения...",
                "popularity": 95.83,
                "rating": 4.95
            },
            {
                "name": "Django",
                "description": "Django — это мощный веб-фреймворк для Python...",
                "popularity": 90.12,
                "rating": 4.85
            }
        ]
        """
        data = request.data  # Получаем данные из запроса

        # Проверяем, является ли data списком
        if isinstance(data, list):
            # Если это список, обрабатываем каждый элемент
            serializer = TechnologySerializer(data=data, many=True)  # Указываем many=True для списка
        else:
            # Если это одиночный объект, обрабатываем его
            serializer = TechnologySerializer(data=data)

        if serializer.is_valid():
            # Если данные валидны, сохраняем технологии
            serializer.save()
            # Возвращаем успешный ответ
            return Response(
                {"message": "Технология/технологии сохранены успешно"},
                status=status.HTTP_201_CREATED
            )

        # Если данные не валидны, преобразуем ошибки в словарь и возвращаем ошибку 400
        errors = parse_errors_to_dict(serializer.errors)
        return Response(
            errors,
            status=status.HTTP_400_BAD_REQUEST
        )