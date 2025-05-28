from django.core.files import File
from django.db import transaction, connection, ProgrammingError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from rest_framework import (
    generics,
    permissions,
    status,
    viewsets
)
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from openpyxl import load_workbook
import pandas as pd
import os
import csv

from .models import Dataset, FileUpload, DataSetTable, DataSetField
from .serializers import (
    DatasetSerializer,
    FileUploadSerializer,
    DataSetTableSerializer,
    DataSetFieldSerializer
)

from ..services.services import (
    create_temp_table_from_source,
    import_file_upload_to_table,
    populate_initial_fields,
    auto_join_table
)


# ==============================================================================
# Dataset endpoints
# ==============================================================================

class DatasetListCreateView(generics.ListCreateAPIView):
    serializer_class   = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        dataset = serializer.save(owner=self.request.user)

        staging_name = import_file_upload_to_table(dataset.file_source.id)
        dataset.table_ref = staging_name
        dataset.save(update_fields=['table_ref'])

        staging_table = DataSetTable.objects.create(
            dataset=dataset,
            connection=dataset.connection,
            table_name=staging_name,
            joined_on={}
        )

        temp_name = create_temp_table_from_source(dataset)
        dataset.table_ref = temp_name
        dataset.save(update_fields=['table_ref'])

        DataSetTable.objects.create(
            dataset=dataset,
            connection=dataset.connection,
            table_name=temp_name,
            joined_on={}
        )

        populate_initial_fields(dataset, temp_name, source_table=staging_table)

class DatasetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /datasets/{pk}/    — детали датасета
    PUT    /datasets/{pk}/    — обновление
    DELETE /datasets/{pk}/    — удаление
    """
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)


# ==============================================================================
# DatasetViewSet (альтернатива generic views)
# ==============================================================================

class DatasetViewSet(viewsets.ModelViewSet):
    """
    Полный CRUD для Dataset через ViewSet.
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        dataset = serializer.save(owner=self.request.user)
        temp_name = create_temp_table_from_source(dataset)
        populate_initial_fields(dataset, temp_name)
        
class DatasetPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        dataset = Dataset.objects.filter(pk=pk, owner=request.user).first()
        if not dataset:
            return Response({"detail": "Not found"}, status=404)

        limit = int(request.query_params.get('limit', 10))
        base_table = dataset.table_ref

        if '.' in base_table:
            schema, table = base_table.split('.', 1)
        else:
            schema, table = 'public', base_table

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f'SELECT * FROM "{schema}"."{table}" LIMIT %s',
                    [limit],
                )
                rows = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
        except ProgrammingError:
            return Response({"detail": f"Table {schema}.{table} does not exist"}, status=404)

        return Response({
            "columns": columns,
            "rows": rows
        })

# ==============================================================================
# DataSetTable endpoints
# ==============================================================================

class DataSetTableViewSet(viewsets.ModelViewSet):
    """
    CRUD для присоединённых таблиц датасета.
    """
    queryset = DataSetTable.objects.all()
    serializer_class = DataSetTableSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        table = serializer.save()
        dataset = table.dataset
        try:
            auto_join_table(dataset, table)
        except ValueError as e:
            raise ValidationError(str(e))
        return super().perform_create(serializer)
    

class RenameDatasetColumnsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        dataset = Dataset.objects.get(pk=pk, owner=request.user)
        renames = request.data.get('renames', [])
        table_ref = dataset.table_ref
        schema, table = ('public', table_ref)
        if '.' in table_ref:
            schema, table = table_ref.split('.', 1)

        with connection.cursor() as cursor:
            for rename in renames:
                cursor.execute(
                    f'ALTER TABLE "{schema}"."{table}" RENAME COLUMN "{rename["old_name"]}" TO "{rename["new_name"]}";'
                )
                DataSetField.objects.filter(
                    dataset=dataset, source_column=rename["old_name"]
                ).update(name=rename["new_name"], source_column=rename["new_name"])
        return Response({"status": "ok"})

# ==============================================================================
# DataSetField endpoints
# ==============================================================================

class DataSetFieldViewSet(viewsets.ModelViewSet):
    """
    CRUD для полей, которые входят в датасет.
    """
    queryset = DataSetField.objects.all()
    serializer_class = DataSetFieldSerializer
    permission_classes = [permissions.IsAuthenticated]

# ==============================================================================
# FileUpload endpoints
# ==============================================================================

class FileUploadView(generics.ListCreateAPIView):
    """
    POST   /upload/       — закачка файла во временную директорию
    GET    /upload/       — список закачанных файлов (для текущего пользователя)
    """
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return FileUpload.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class FileUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /upload/{pk}/    — метаданные + предпросмотр содержимого
    PUT    /upload/{pk}/    — изменить имя/загрузить новый файл
    DELETE /upload/{pk}/    — удалить запись и файл на диске
    """
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return FileUpload.objects.filter(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        if not instance.file or not hasattr(instance.file, 'path'):
            data['parsed'] = []
            return Response(data)

        encoding   = request.query_params.get('encoding', 'utf-8')
        delimiter  = request.query_params.get('delimiter', ',')
        has_header = request.query_params.get('has_header', 'true').lower() == 'true'

        try:
            if instance.file_type in ('csv', 'txt'):
                parsed = self._parse_csv(instance.file.path, encoding, delimiter, has_header)

            elif instance.file_type == 'xlsx':
                parsed, sheets = self._parse_xlsx(instance.file.path, has_header)
                data['sheets'] = sheets

            else:
                raise ValidationError(f"Неподдерживаемый тип файла: {instance.file_type}")

            data['parsed'] = parsed
            return Response(data)

        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        file = self.request.FILES.get('file')
        name = self.request.data.get('name')

        file_type = (file.name.split('.')[-1].lower()
                     if file else 
                     (name.split('.')[-1].lower() if name and '.' in name else None))

        serializer.save(
            name=name or serializer.instance.name,
            original_filename=(file.name if file else serializer.instance.original_filename),
            file=(file if file else serializer.instance.file),
            file_type=file_type
        )

    def perform_destroy(self, instance):
        # удаляем сам файл
        if instance.file and os.path.isfile(instance.file.path):
            try:
                os.remove(instance.file.path)
            except PermissionError:
                import gc
                gc.collect()
                raise ValidationError("Файл занят другим процессом.")
        instance.delete()

    # -----------------------------
    # вспомогательные методы
    # -----------------------------
    @staticmethod
    def _parse_csv(path, encoding, delimiter, has_header):
        with open(path, 'r', encoding=encoding) as f:
            reader = csv.reader(f, delimiter='\t' if delimiter == '\\t' else delimiter)
            rows = list(reader)
        if not has_header and rows:
            alph = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            headers = [alph[i] if i < len(alph) else f"Col{i}" for i in range(len(rows[0]))]
            rows.insert(0, headers)
        return rows

    @staticmethod
    def _parse_xlsx(path, has_header):
        wb = load_workbook(filename=path, read_only=True)
        sheet = wb.sheetnames[0]
        ws = wb[sheet]
        data = list(ws.values)
        if not has_header:
            return data, wb.sheetnames
        headers, *body = data
        return [list(headers), *body], wb.sheetnames

class FileUploadByConnectionView(generics.ListAPIView):
    """
    GET /connection/{id}/files/ — файлы, загруженные к указанному соединению
    """
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conn_id = self.kwargs['connection_id']
        return FileUpload.objects.filter(owner=self.request.user, connection_id=conn_id).order_by('-uploaded_at')

class FinalizeUploadView(APIView):
    """
    POST /upload/finalize/  — сохраняет временный файл во FileUpload-модель.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        temp_path         = request.data.get('temp_path')
        name              = request.data.get('name')
        original_filename = request.data.get('original_filename')
        file_type         = request.data.get('file_type')
        connection_id     = request.data.get('connection')

        if not all([temp_path, name, original_filename, file_type]):
            return Response(
                {"error": "Необходимы поля temp_path, name, original_filename, file_type"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not os.path.exists(temp_path):
            return Response({"error": "Временный файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        # создаём запись, сохраняем файл из temp_path
        upload = FileUpload(
            owner=request.user,
            name=name,
            original_filename=original_filename,
            file_type=file_type,
            connection_id=connection_id
        )

        with open(temp_path, 'rb') as f:
            upload.file.save(original_filename, File(f), save=False)
        upload.save()

        # удаляем временный файл
        try:
            os.remove(temp_path)
        except OSError:
            pass

        serializer = FileUploadSerializer(upload)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# ==============================================================================
# XLSX helper endpoints
# ==============================================================================

class XlsxSheetListView(APIView):
    """
    POST /xlsx/sheets/   — получить список листов в загруженном .xlsx-файле
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file or not file.name.endswith('.xlsx'):
            raise ValidationError("Ожидался .xlsx файл")

        try:
            wb = load_workbook(filename=file, read_only=True)
            return Response({"filename": file.name, "sheets": wb.sheetnames})
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

class XlsxTempPreviewView(APIView):
    """
    POST /xlsx/preview/  — предпросмотр содержимого временного .xlsx-файла
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        temp_path     = request.data.get('temp_path')
        has_header    = request.data.get('has_header', 'true').lower() == 'true'

        if not temp_path or not os.path.exists(temp_path):
            return Response({"error": "Временный файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        try:
            df     = pd.read_excel(temp_path, header=0 if has_header else None)
            values = df.fillna('').astype(str).values.tolist()
            if has_header:
                values.insert(0, list(df.columns))
            return Response({"parsed": values})
        except Exception as exc:
            return Response({"error": f"Ошибка при чтении Excel: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
