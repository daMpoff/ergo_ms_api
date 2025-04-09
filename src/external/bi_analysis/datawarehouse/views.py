from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import StagingGenericData
from .serializers import StagingGenericDataSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Создавайте свои представления здесь

class StagingDataView(APIView):
    @swagger_auto_schema(
        operation_summary="Добавление сырой записи",
        request_body=StagingGenericDataSerializer,
        responses={
            201: openapi.Response("Успех", StagingGenericDataSerializer),
            400: "Ошибка валидации",
        }
    )
    def post(self, request):
        serializer = StagingGenericDataSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            return Response(StagingGenericDataSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Получение списка сырой информации",
        responses={
            200: openapi.Response("Успех", StagingGenericDataSerializer(many=True)),
        }
    )
    def get(self, request):
        # Можно добавить фильтрацию, например по processed или source
        queryset = StagingGenericData.objects.all().order_by('-ingest_timestamp')
        serializer = StagingGenericDataSerializer(queryset, many=True)
        return Response(serializer.data)