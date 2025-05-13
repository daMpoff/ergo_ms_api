from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.core.utils.database.base import SqlAlchemyManager
from src.core.utils.database.dbconfig import DBConfig
from src.core.utils.database.main import OrderedDictQueryExecutor
from src.core.utils.management.commands.add_module import Command
from django.contrib.auth import authenticate
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
import logging
from django.contrib.auth.models import User

from src.core.utils.methods import (
    parse_errors_to_dict, 
    send_confirmation_email
)
from src.core.cms.adp.models import EmailConfirmationCode
from src.core.cms.adp.serializers import (
    UserLoginSerializer, 
    UserRegistrationSerializer,
    UserRegistrationValidationSerializer,
)
from src.core.utils.base.base_views import BaseAPIView
from src.core.cms.queries import (get_users_permissions, get_users_group, get_users_group_permissions)
import requests
from rest_framework.request import Request
import pandas as pd
from src.external.expsys_module.models import (Skill, Vacance)
from django.db import connection
from src.external.lms.models import Subject
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class TeacherSubjectsView(APIView):
    @swagger_auto_schema(
        operation_description="Получение всех предметов по ID учителя из query-параметра",
        manual_parameters=[
            openapi.Parameter(
                'user_id', openapi.IN_QUERY, description="ID пользователя", type=openapi.TYPE_INTEGER, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Список предметов учителя",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'creationdate': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'lastupdate': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                    'teacher_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Неверный запрос",
            404: "Пользователь не найден",
            403: "Пользователь не является учителем",
            500: "Внутренняя ошибка сервера"
        }
    )
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')

            if not user_id:
                return Response(
                    {"error": "user_id обязателен", "message": "Укажите ID пользователя в параметрах запроса."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден", "message": f"Пользователь с ID {user_id} не существует."},
                    status=status.HTTP_404_NOT_FOUND
                )


            teacher_subjects = Subject.objects.filter(teacher=user)

            subjects_data = [{
                'id': subject.id,
                'name': subject.name,
                'description': subject.description,
                'creationdate': subject.creationdate,
                'lastupdate': subject.lastupdate,
                'teacher_id': subject.teacher.id,
            } for subject in teacher_subjects]

            return Response(
                {
                    "data": subjects_data,
                    "message": f"Найдено {len(subjects_data)} предметов."
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при получении предметов."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
logger = logging.getLogger(__name__)

class SubjectCreateView(APIView):
    def post(self, request):
        try:
            # Валидация данных
            name = request.data.get('name', '').strip()
            description = request.data.get('description', '').strip()

            if not name:
                return Response(
                    {
                        "status": "error",
                        "message": "Название предмета обязательно"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверка на авторизацию
            if not request.user.is_authenticated:
                return Response(
                    {
                        "status": "error",
                        "message": "Требуется авторизация"
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Создание предмета
            subject = Subject.objects.create(
                name=name,
                description=description,
                teacher=request.user
            )

            # Формирование успешного ответа
            return Response(
                {
                    "status": "success",
                    "data": {
                        "id": subject.id,
                        "name": subject.name,
                        "description": subject.description,
                        "teacher_id": subject.teacher.id,
                        "creation_date": subject.creationdate.strftime('%Y-%m-%d'),  # Форматируем дату
                        "icon": "book",
                        "icon_background": "bg-blue",
                        "stats": {
                            "students": 0,
                            "lessons": 0,
                            "tasks": 0
                        }
                    }
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            # Логирование исключений
            logger.error(f"Ошибка при создании предмета: {str(e)}")
            return Response(
                {
                    "status": "error",
                    "message": "Внутренняя ошибка сервера",
                    "details": str(e)  # Включаем дополнительные детали ошибки для диагностики
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class PostCompetenciesandVacations(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Запись компетенций и вакансий.",
        responses={
            200: "компетенции записаны",
            401: "Не удалось записать компетенции"
        },
    )
    def post(self, request: Request):
        url = "https://api.hh.ru/vacancies?per_page=100&experience=noExperience&text=Программист"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            vacancies = data.get('items', [])
            df = pd.DataFrame(vacancies).iloc[:, 0].tolist()
            allcompec = []
            for id in df:
                urltemp = "https://api.hh.ru/vacancies/"+id
                responset = requests.get(urltemp)
                if response.status_code == 200:
                    data = responset.json()
                    t = data['key_skills']
                    l = []
                    for i in t:
                        l.append(i['name'])
                    allcompec.append(l)
            uniquecompecs =[]
            for com in allcompec:
                for par in com:
                    if uniquecompecs.count(par)==0:
                        uniquecompecs.append(par)
            uniquecompecs.sort()
            dictlist =[]
            key =['name']
            for i in range(0,len(uniquecompecs)):
                dictlist.append(dict.fromkeys(key,uniquecompecs[i]))
            table_name = Skill._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;")
            for item in dictlist:
                Skill.objects.create(**item)
            df = pd.DataFrame(vacancies)
            vacancies_df = df['name'].to_frame()
            salary = df['salary'].apply(pd.Series)
            area = df['area'].apply(pd.Series)
            types = df['type'].apply(pd.Series)
            experience = df['experience'].apply(pd.Series)
            employment = df['employment'].apply(pd.Series)
            vacancies_df['salary_from'] = salary['from']
            vacancies_df['salary_to'] = salary['to']
            vacancies_df['currency'] = salary['currency']
            vacancies_df['area'] = area['name']
            vacancies_df['type'] = types['name']
            vacancies_df['employment'] = employment['name']
            vacancies_df['experience'] = experience['name']
            sck = pd.DataFrame({'Compec': allcompec})
            records = vacancies_df.to_dict('records')
            sck = sck.to_dict('records')
            table_name = Vacance._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;")
            for item in records:
                Vacance.objects.create(**item)
            for i in range(0, len(sck)):
                vac = Vacance.objects.get(id=i+1)
                for item in sck[i]['Compec']:
                    skill = Skill.objects.get(name=item)
                    vac.skill.add(skill)
            return Response(
            uniquecompecs,
            status=status.HTTP_200_OK
        )