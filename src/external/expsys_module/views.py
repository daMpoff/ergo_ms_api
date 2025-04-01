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