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

from rest_framework.request import Request

class GetUserPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав пользователя.",
        responses={
            200: "Права пользователя получены",
            401: "Не удалось получить права пользователя"
        },
        manual_parameters=[
            openapi.Parameter('user_name', openapi.IN_QUERY, description='имя пользователя', type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request: Request):
        name = request.query_params.get('user_name')
        result = OrderedDictQueryExecutor.fetchall(
            get_users_permissions,
            name,
        )

        # config = DBConfig()
        # dbmanager = SqlAlchemyManager(config=config)

        # result1 = dbmanager.fetchall(
        #     get_users_permissions,
        #     id
        # )
        # print(result1)
        
        return Response(
            result,
            status=status.HTTP_200_OK
        )
    
class GetUserGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение групп пользователя.",
        responses={
            200: "группы пользователя получены",
            401: "Не удалось получить группы пользователя"
        },
        manual_parameters=[
            openapi.Parameter('user_name', openapi.IN_QUERY, description='имя пользователя', type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request: Request):
        name = request.query_params.get('user_name')
        result = OrderedDictQueryExecutor.fetchall(
            get_users_group,
            name,
        )
        return Response(
            result,
            status=status.HTTP_200_OK
        )
    
class GetUserGroupPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав пользователя через его группу.",
        responses={
            200: "Права пользователя получены",
            401: "Не удалось получить права пользователя"
        },
        manual_parameters=[
            openapi.Parameter('user_name', openapi.IN_QUERY, description='имя пользователя', type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request: Request):
        name = request.query_params.get('user_name')
        result = OrderedDictQueryExecutor.fetchall(
            get_users_group_permissions,
            name,
        )
        return Response(
            result,
            status=status.HTTP_200_OK
        )