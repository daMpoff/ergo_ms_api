from rest_framework import generics, permissions
from .models import Dataset, FileUpload
from .serializers import DatasetSerializer, FileUploadSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from openpyxl import load_workbook
from rest_framework.views import APIView
from django.core.files import File
import os, csv, tempfile

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

class FileUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            raise ValidationError("Файл не найден.")

        name = request.data.get('name') or file.name

        try:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, name)
            with open(temp_path, 'wb+') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
        except Exception as e:
            raise ValidationError(f"Ошибка сохранения временного файла: {str(e)}")

        return Response({
            'temp_path': temp_path,
            'original_filename': file.name,
            'file_type': file.name.split('.')[-1].lower()
        })

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
        return FileUpload.objects.filter(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        if not instance.file or not hasattr(instance.file, 'path'):
            data = serializer.data
            data['parsed'] = []
            return Response(data)

        encoding = request.query_params.get('encoding', 'utf-8')
        delimiter = request.query_params.get('delimiter', ',')
        has_header = request.query_params.get('has_header', 'true').lower() == 'true'

        try:
            if instance.file_type == 'csv':
                with open(instance.file.path, 'r', encoding=encoding) as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    parsed = list(reader)
                    if parsed and not has_header:
                        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        col_count = len(parsed[0])
                        headers = [alphabet[i] if i < len(alphabet) else f"Col {i + 1}" for i in range(col_count)]
                        parsed.insert(0, headers)

            elif instance.file_type == 'xlsx':
                import pandas as pd
                xls = pd.ExcelFile(instance.file.path)

                sheet_name = request.query_params.get('sheet') or xls.sheet_names[0]
                df = pd.read_excel(xls, sheet_name=sheet_name, header=0 if has_header else None)
                parsed = df.fillna('').astype(str).values.tolist()
                if has_header:
                    parsed.insert(0, list(df.columns))

                data = serializer.data
                data['sheets'] = xls.sheet_names
                data['parsed'] = parsed
                return Response(data)

            else:
                raise ValueError(f'Неподдерживаемый тип файла: {instance.file_type}')

        except Exception as e:
            return Response({'error': f'Ошибка при чтении файла: {str(e)}'}, status=500)

        data = serializer.data
        data['parsed'] = parsed
        return Response(data)

    def perform_update(self, serializer):
        name = self.request.data.get('name')
        file = self.request.FILES.get('file')

        file_type = None
        if file:
            file_type = file.name.split('.')[-1].lower()
        elif name and '.' in name:
            file_type = name.split('.')[-1].lower()

        serializer.save(
            name=name or serializer.instance.name,
            original_filename=file.name if file else serializer.instance.original_filename,
            file=file if file else serializer.instance.file,
            file_type=file_type
        )

    def perform_destroy(self, instance):
        try:
            if instance.file and os.path.isfile(instance.file.path):
                try:
                    os.remove(instance.file.path)
                except PermissionError:
                    import gc
                    gc.collect()
                    raise ValidationError("Файл занят другим процессом.")
        finally:
            instance.delete()

class XlsxSheetListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file or not file.name.endswith('.xlsx'):
            raise ValidationError("Ожидался .xlsx файл")

        try:
            wb = load_workbook(filename=file, read_only=True)
            sheet_names = wb.sheetnames
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        return Response({
            "filename": file.name,
            "sheets": sheet_names
        })

class FinalizeUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        temp_path = request.data.get('temp_path')
        name = request.data.get('name')
        original_filename = request.data.get('original_filename')
        file_type = request.data.get('file_type')

        if not all([temp_path, name, original_filename, file_type]):
            return Response({"error": "Необходимы поля: temp_path, name, original_filename, file_type"}, status=400)

        if not os.path.exists(temp_path):
            return Response({"error": "Временный файл не найден"}, status=404)

        file_upload = FileUpload(
            owner=request.user,
            name=name,
            original_filename=original_filename,
            file_type=file_type
        )

        with open(temp_path, 'rb') as f:
            file_upload.file.save(original_filename, File(f), save=False)

        file_upload.save()
        os.remove(temp_path)  # удаляем временный файл

        return Response(FileUploadSerializer(file_upload).data, status=status.HTTP_201_CREATED)
    
class XlsxTempPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        temp_path = request.data.get('temp_path')
        has_header_str = request.data.get('has_header', 'true')
        has_header = has_header_str.lower() == 'true'

        if not temp_path or not os.path.exists(temp_path):
            return Response({"error": "Временный файл не найден"}, status=404)

        try:
            import pandas as pd
            df = pd.read_excel(temp_path, header=0 if has_header else None)
            parsed = df.fillna('').astype(str).values.tolist()
            if has_header:
                parsed.insert(0, list(df.columns))
        except Exception as e:
            return Response({"error": f"Ошибка при чтении Excel: {str(e)}"}, status=500)

        return Response({
            "parsed": parsed
        })
