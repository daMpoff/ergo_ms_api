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
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import *
from .serializers import *

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
class GeneralSettingsViewSet(viewsets.ModelViewSet):
        queryset = GeneralSettings.objects.all()
        serializer_class = GeneralSettingsSerializer

class AppearanceSettingsViewSet(viewsets.ModelViewSet):
    queryset = AppearanceSettings.objects.all()
    serializer_class = AppearanceSettingsSerializer

class SEOSettingsViewSet(viewsets.ModelViewSet):
    queryset = SEOSettings.objects.all()
    serializer_class = SEOSettingsSerializer

class SecuritySettingsViewSet(viewsets.ModelViewSet):
    queryset = SecuritySettings.objects.all()
    serializer_class = SecuritySettingsSerializer

class MediaSettingsViewSet(viewsets.ModelViewSet):
    queryset = MediaSettings.objects.all()
    serializer_class = MediaSettingsSerializer

class PermalinkSettingsViewSet(viewsets.ModelViewSet):
    queryset = PermalinkSettings.objects.all()
    serializer_class = PermalinkSettingsSerializer

class EmailSettingsViewSet(viewsets.ModelViewSet):
    queryset = EmailSettings.objects.all()
    serializer_class = EmailSettingsSerializer
class FileViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        file = request.FILES.get('file')

        if not file:
            return Response({'error': 'Файл не передан'}, status=status.HTTP_400_BAD_REQUEST)

        instance = UploadedFile.objects.create(file=file)
        return Response(UploadedFileSerializer(instance).data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # удаляем файл с диска, но не трогаем запись
        instance.file.delete(save=False)
        # затем удаляем запись из БД
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)