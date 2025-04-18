from rest_framework import generics, permissions
from .models import Dataset, FileUpload
from .serializers import DatasetSerializer, FileUploadSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
import os

class DatasetListCreateView(generics.ListCreateAPIView):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DatasetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)
    
class FileUploadView(generics.CreateAPIView):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        if not file:
            raise ValidationError("Файл не найден.")

        name = self.request.data.get('name') or file.name

        if FileUpload.objects.filter(owner=self.request.user, name=name, original_filename=file.name).exists():
            raise ValidationError(f'Файл с именем "{name}" уже существует.')

        serializer.save(
            owner=self.request.user,
            original_filename=file.name,
            name=name,
            file_type=file.name.split('.')[-1].lower()
        )
        
class FileUploadListView(generics.ListAPIView):
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FileUpload.objects.filter(owner=self.request.user).order_by('-uploaded_at')
    
class FileUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ограничиваем доступ только к своим файлам
        return FileUpload.objects.filter(owner=self.request.user)

    def perform_update(self, serializer):
        file = self.request.FILES.get('file')
        name = self.request.data.get('name') or (file.name if file else None)

        serializer.save(
            original_filename=file.name if file else None,
            name=name,
            file_type=file.name.split('.')[-1].lower() if file else None
        )

    def perform_destroy(self, instance):
        # Удаляем файл физически
        if instance.file and os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
        instance.delete()