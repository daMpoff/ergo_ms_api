from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated

from .models import GenericStorage
from .serializers import GenericStorageSerializer
from .services.file_parser import auto_parse_uploaded_file


class GenericStorageView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Сохранить JSON или файл",
        operation_description="Можно загрузить JSON-файл, CSV или Excel. Данные будут сохранены автоматически.",
        request_body=GenericStorageSerializer,
        responses={
            201: openapi.Response("Успех", GenericStorageSerializer),
            400: openapi.Response("Ошибка валидации"),
            500: openapi.Response("Внутренняя ошибка сервера")
        }
    )
    def post(self, request):
        data = request.data.copy()
        file = request.FILES.get('file')

        if file and not data.get('json_data'):
            try:
                parsed = auto_parse_uploaded_file(file)
                data['json_data'] = parsed
            except Exception as e:
                return Response({'error': f'Ошибка чтения файла: {str(e)}'}, status=400)

        serializer = GenericStorageSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save(owner=request.user)
            return Response(GenericStorageSerializer(instance).data, status=201)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("storage_type", openapi.IN_QUERY, description="Фильтрация по типу хранения", type=openapi.TYPE_STRING),
            openapi.Parameter("name", openapi.IN_QUERY, description="Фильтрация по имени источника", type=openapi.TYPE_STRING),
            openapi.Parameter("created_after", openapi.IN_QUERY, description="Фильтрация по дате (>=)", type=openapi.TYPE_STRING, format="date-time"),
            openapi.Parameter("created_before", openapi.IN_QUERY, description="Фильтрация по дате (<=)", type=openapi.TYPE_STRING, format="date-time"),
        ],
        operation_summary="Получить список сохранённых объектов",
        operation_description="Поддерживает фильтрацию по типу хранения, имени и дате создания.",
        responses={
            200: openapi.Response("Успех", GenericStorageSerializer(many=True)),
            400: openapi.Response("Ошибка валидации"),
            500: openapi.Response("Внутренняя ошибка сервера"),
        }
    )
    def get(self, request):
        queryset = GenericStorage.objects.filter(owner=request.user)

        if storage_type := request.query_params.get('storage_type'):
            queryset = queryset.filter(storage_type=storage_type)

        if name := request.query_params.get('name'):
            queryset = queryset.filter(name__icontains=name)

        if created_after := request.query_params.get('created_after'):
            queryset = queryset.filter(created_at__gte=parse_datetime(created_after))

        if created_before := request.query_params.get('created_before'):
            queryset = queryset.filter(created_at__lte=parse_datetime(created_before))

        serializer = GenericStorageSerializer(queryset.order_by('-created_at'), many=True)
        return Response(serializer.data)


class FileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Загрузка файла (CSV, JSON, Excel)",
        operation_description="Загружает файл и сохраняет его содержимое в формате JSON",
        manual_parameters=[
            openapi.Parameter("storage_type", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("name", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("description", openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("table_ref", openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("file", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
        ],
        responses={
            201: openapi.Response("Успешно", GenericStorageSerializer),
            400: "Ошибка запроса",
            500: "Ошибка сервера",
        }
    )
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Файл обязателен."}, status=400)

        try:
            parsed_data = auto_parse_uploaded_file(file)
        except Exception as e:
            return Response({"error": f"Ошибка при разборе файла: {str(e)}"}, status=400)

        record_data = {
            "storage_type": request.data.get("storage_type"),
            "name": request.data.get("name"),
            "description": request.data.get("description"),
            "table_ref": request.data.get("table_ref"),
            "json_data": parsed_data,
        }

        serializer = GenericStorageSerializer(data=record_data)
        if serializer.is_valid():
            instance = serializer.save(owner=request.user)
            return Response(GenericStorageSerializer(instance).data, status=201)
        return Response(serializer.errors, status=400)
