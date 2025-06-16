from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.core.utils.base.base_views import BaseAPIView
from src.core.cms.adp.queries import ( get_tasks_by_month, get_tasks_by_priority, get_tasks_by_section,
    get_project_completion_stats, get_user_productivity_stats, 
    get_deadline_analysis, get_task_creation_trend,
    get_project_timeline_stats, get_calendar_activity_stats,
    get_task_complexity_stats )
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
        
class ProjectCompletionStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики завершенности проектов с процентами выполнения",
        responses={
            200: "Статистика завершенности проектов",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            completion_stats = get_project_completion_stats()
    
            if not completion_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика по проектам не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": completion_stats,
                "message": "Статистика завершенности проектов получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserProductivityStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики продуктивности пользователей",
        responses={
            200: "Статистика продуктивности пользователей",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            productivity_stats = get_user_productivity_stats()
    
            if not productivity_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика продуктивности не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": productivity_stats,
                "message": "Статистика продуктивности получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeadlineAnalysisView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение анализа дедлайнов задач (просроченные, критические, будущие)",
        responses={
            200: "Анализ дедлайнов задач",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            deadline_stats = get_deadline_analysis()
    
            if not deadline_stats:
                response_data = {
                    "data": [],
                    "message": "Данные по дедлайнам не найдены"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": deadline_stats,
                "message": "Анализ дедлайнов получен успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении анализа дедлайнов: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TaskCreationTrendView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение тренда создания задач за последние 30 дней",
        responses={
            200: "Тренд создания задач",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            trend_stats = get_task_creation_trend()
    
            if not trend_stats:
                response_data = {
                    "data": [],
                    "message": "Данные по трендам не найдены"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": trend_stats,
                "message": "Тренд создания задач получен успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении тренда: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProjectTimelineStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики временных рамок проектов",
        responses={
            200: "Статистика временных рамок проектов",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            timeline_stats = get_project_timeline_stats()
    
            if not timeline_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика временных рамок не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": timeline_stats,
                "message": "Статистика временных рамок получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CalendarActivityStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики активности календаря по дням недели и времени",
        responses={
            200: "Статистика активности календаря",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            activity_stats = get_calendar_activity_stats()
    
            if not activity_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика активности календаря не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": activity_stats,
                "message": "Статистика активности календаря получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики календаря: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TaskComplexityStatsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение статистики сложности задач (приоритет, подзадачи, время выполнения)",
        responses={
            200: "Статистика сложности задач",
            500: "Ошибка сервера при получении данных"
        }
    )
    def get(self, request):
        try:
            complexity_stats = get_task_complexity_stats()
    
            if not complexity_stats:
                response_data = {
                    "data": [],
                    "message": "Статистика сложности задач не найдена"
                }
                return Response(response_data, status=status.HTTP_200_OK)
    
            response_data = {
                "data": complexity_stats,
                "message": "Статистика сложности задач получена успешно"
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"Произошла ошибка при получении статистики сложности: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )