from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.core.utils.base.base_views import BaseAPIView
from src.core.cms.adp.queries import get_tasks_by_month, get_tasks_by_priority, get_tasks_by_section
from rest_framework import viewsets, status
from rest_framework.decorators import action
from .models import Project, Section, Task, Calendar
from django.contrib.auth import get_user_model
from .serializers import ProjectSerializer, SectionSerializer, TaskSerializer, CalendarSerializer, UserSerializer, UserProjectSerializer
from django.apps import apps
from django.db import connection, transaction
from rest_framework.generics import get_object_or_404

User = get_user_model()
User_Project = apps.get_model('crm', 'User_Project')

# Класс представления для получения статистики задач по месяцам
class MonthlyStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики задач по месяцам. Если указан параметр 'year', возвращается статистика за указанный год. Если параметр 'year' не указан, возвращается статистика за текущий год.",
        manual_parameters=[
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Год, за который нужно получить статистику (опционально)",
            ),
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Месяц, за который нужно получить статистику (опционально)",
            )
        ],
        responses={
            200: "Статистика задач по месяцам",
            400: "Ошибка в параметрах запроса",
            404: "Данные не найдены"
        }
    )
    def get(self, request):
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        query_params = {}
        if year:
            try:
                query_params['year'] = int(year)
            except ValueError:
                return Response(
                    {"message": "Значение параметра 'year' должно быть целым числом"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if month:
            try:
                month_value = int(month)
                if 1 <= month_value <= 12:
                    query_params['month'] = month_value
                else:
                    return Response(
                        {"message": "Значение параметра 'month' должно быть в диапазоне от 1 до 12"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"message": "Значение параметра 'month' должно быть целым числом"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Получаем данные о задачах по месяцам
        try:
            tasks_stats = get_tasks_by_month(**query_params)
    
            if not tasks_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика по задачам не найдена для указанного периода"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": tasks_stats,
                "message": "Статистика по задачам получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PriorityStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики задач по приоритетам, с разбивкой на выполненные и невыполненные",
        responses={
            200: "Статистика задач по приоритетам",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            priority_stats = get_tasks_by_priority()
    
            if not priority_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика по задачам не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": priority_stats,
                "message": "Статистика по задачам получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        Project.objects.bulk_create([Project(**item) for item in serializer.validated_data])

    @swagger_auto_schema(
        operation_description="Удаление всех проектов и связанных с ними данных",
        responses={
            204: "Данные успешно удалены",
            500: "Ошибка при удалении данных"
        }
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        try:
            with transaction.atomic():
                Task.objects.all().delete()
                Section.objects.all().delete()
                User_Project.objects.all().delete()
                Project.objects.all().delete()
                
                # Сброс последовательностей
                with connection.cursor() as cursor:
                    cursor.execute("ALTER SEQUENCE crm_task_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE crm_section_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE crm_user_project_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE crm_project_id_seq RESTART WITH 1")
                
            return Response({"message": "Все проекты и связанные данные успешно удалены"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"Ошибка при удалении данных: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        Section.objects.bulk_create([Section(**item) for item in serializer.validated_data])

    @swagger_auto_schema(
        operation_description="Удаление всех секций и связанных задач",
        responses={
            204: "Данные успешно удалены",
            500: "Ошибка при удалении данных"
        }
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        try:
            with transaction.atomic():
                Task.objects.all().delete()
                Section.objects.all().delete()
                
                # Сброс последовательностей
                with connection.cursor() as cursor:
                    cursor.execute("ALTER SEQUENCE crm_task_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE crm_section_id_seq RESTART WITH 1")
                
            return Response({"message": "Все секции и задачи успешно удалены"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"Ошибка при удалении данных: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        Task.objects.bulk_create([Task(**item) for item in serializer.validated_data])

    @swagger_auto_schema(
        operation_description="Удаление всех задач",
        responses={
            204: "Данные успешно удалены",
            500: "Ошибка при удалении данных"
        }
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        try:
            with transaction.atomic():
                Task.objects.all().delete()
                
                # Сброс последовательности
                with connection.cursor() as cursor:
                    cursor.execute("ALTER SEQUENCE crm_task_id_seq RESTART WITH 1")
                
            return Response({"message": "Все задачи успешно удалены"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"Ошибка при удалении данных: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CalendarViewSet(viewsets.ModelViewSet):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        Calendar.objects.bulk_create([Calendar(**item) for item in serializer.validated_data])

    @swagger_auto_schema(
        operation_description="Удаление всех календарных записей",
        responses={
            204: "Данные успешно удалены",
            500: "Ошибка при удалении данных"
        }
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        try:
            with transaction.atomic():
                Calendar.objects.all().delete()
                
                # Сброс последовательности
                with connection.cursor() as cursor:
                    cursor.execute("ALTER SEQUENCE crm_calendar_id_seq RESTART WITH 1")
                
            return Response({"message": "Все календарные записи успешно удалены"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"Ошибка при удалении данных: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserProjectViewSet(viewsets.ModelViewSet):
    queryset = User_Project.objects.all()
    serializer_class = UserProjectSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        User_Project.objects.bulk_create([User_Project(**item) for item in serializer.validated_data])

    @swagger_auto_schema(
        operation_description="Удаление всех связей пользователей с проектами",
        responses={
            204: "Данные успешно удалены",
            500: "Ошибка при удалении данных"
        }
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        try:
            with transaction.atomic():
                User_Project.objects.all().delete()
                
                # Сброс последовательности
                with connection.cursor() as cursor:
                    cursor.execute("ALTER SEQUENCE crm_user_project_id_seq RESTART WITH 1")
                
            return Response({"message": "Все связи пользователей с проектами успешно удалены"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"Ошибка при удалении данных: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        User.objects.bulk_create([User(**item) for item in serializer.validated_data])

    @swagger_auto_schema(
        operation_description="Удаление всех пользователей и связанных данных",
        responses={
            204: "Данные успешно удалены",
            500: "Ошибка при удалении данных"
        }
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        try:
            with transaction.atomic():
                Task.objects.all().delete()
                User_Project.objects.all().delete()
                Calendar.objects.all().delete()
                User.objects.all().delete()
                
                # Сброс последовательностей
                with connection.cursor() as cursor:
                    cursor.execute("ALTER SEQUENCE crm_task_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE crm_user_project_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE crm_calendar_id_seq RESTART WITH 1")
                    cursor.execute("ALTER SEQUENCE auth_user_id_seq RESTART WITH 1")
                
            return Response({"message": "Все пользователи и связанные данные успешно удалены"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"Ошибка при удалении данных: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SectionStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики задач по секциям",
        responses={
            200: "Статистика задач по секциям",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            section_stats = get_tasks_by_section()
    
            if not section_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика по секциям не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": section_stats,
                "message": "Статистика по секциям получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )