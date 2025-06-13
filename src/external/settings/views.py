from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.decorators import action
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

from rest_framework.request import Request
from rest_framework.parsers import MultiPartParser, FormParser

from .models import *
from .serializers import *

class GeneralSettingsViewSet(viewsets.ModelViewSet):
    queryset = GeneralSettings.objects.all()
    serializer_class = GeneralSettingsSerializer

    @action(detail=False, methods=['get'], url_path='last')
    def get_last_settings(self, request):
        last_settings = self.queryset.order_by('-id').first()
        if last_settings:
            serializer = self.get_serializer(last_settings)
            return Response(serializer.data)
        return Response({'detail': 'Нет ни одной записи настроек.'}, status=status.HTTP_404_NOT_FOUND)

class AppearanceSettingsViewSet(viewsets.ModelViewSet):
    queryset = AppearanceSettings.objects.all()
    serializer_class = AppearanceSettingsSerializer

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
        alt_name = request.data.get('alt_name', '')

        if not file:
            return Response({'error': 'Файл не передан'}, status=status.HTTP_400_BAD_REQUEST)

        instance = UploadedFile.objects.create(file=file, alt_name=alt_name)
        return Response(UploadedFileSerializer(instance).data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.file.delete(save=False)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    