from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.external.crm.models import Project, User_Project
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class UserAllProjectsView(APIView):
    @swagger_auto_schema(
        operation_description="Получение всех проектов пользователя",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="ID пользователя",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Список проектов пользователя",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'dateofcreation': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'creator_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'deadline': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Не указан ID пользователя",
            404: "Пользователь не найден",
            500: "Внутренняя ошибка сервера"
        }
    )
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response(
                    {"error": "Необходимо указать user_id", "message": "Ошибка валидации."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден", "message": "Ошибка валидации."},
                    status=status.HTTP_404_NOT_FOUND
                )
            user_projects = User_Project.objects.filter(user_id=user_id).select_related('project')
            projects_data = [{
                'id': user_project.project.id,
                'name': user_project.project.name,
                'dateofcreation': user_project.project.dateofcreation,
                'creator_id': user_project.project.creator_id,
                'user_id': user_project.user_id,
                'deadline': user_project.project.deadline,
                'description': user_project.project.description,
            } for user_project in user_projects]
            return Response(
                {
                    "data": projects_data,
                    "message": f"Найдено {len(projects_data)} проектов."
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при получении проектов."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProjectCreateView(APIView):
    def post(self, request):
        try:
            # Валидация данных
            name = request.data.get('name', '').strip()
            description = request.data.get('description', '').strip()
            deadline_str = request.data.get('deadline', '').strip()
            if not name:
                return Response(
                    {"message": "Название проекта обязательно"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Проверка на авторизацию
            if not request.user.is_authenticated:
                return Response(
                    {"message": "Требуется авторизация"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            # Парсинг даты дедлайна
            deadline = timezone.now().date()  # Значение по умолчанию
            if deadline_str:
                try:
                    deadline = timezone.datetime.strptime(deadline_str, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {"message": "Неверный формат даты. Используйте YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            # Создание проекта
            project = Project.objects.create(
                name=name,
                description=description,
                deadline=deadline,
                creator=request.user,
            )
            # Автоматически добавляем создателя в проект
            user_project = User_Project.objects.create(
                project=project,
                user=request.user,
                isnew=True
            )
            # Формирование успешного ответа
            return Response(
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "creator_id": project.creator.id,
                    "dateofcreation": project.dateofcreation.strftime('%Y-%m-%d'),
                    "deadline": project.deadline.strftime('%Y-%m-%d'),
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Ошибка при создании проекта: {str(e)}", exc_info=True)
            return Response(
                {
                    "message": "Внутренняя ошибка сервера",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProjectCreateView(APIView):
    def post(self, request):
        try:
            # Валидация данных
            project_id = request.data.get('project_id')
            user_id = request.data.get('user_id')
            isnew = request.data.get('isnew', True)  # Значение по умолчанию True
            if not project_id or not user_id:
                return Response(
                    {"message": "Необходимо указать project_id и user_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Проверка на авторизацию
            if not request.user.is_authenticated:
                return Response(
                    {"message": "Требуется авторизация"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            # Проверка существования проекта и пользователя
            try:
                project = Project.objects.get(pk=project_id)
                user = User.objects.get(pk=user_id)
            except (Project.DoesNotExist, User.DoesNotExist) as e:
                return Response(
                    {"message": "Проект или пользователь не найдены"},
                    status=status.HTTP_404_NOT_FOUND
                )
            # Проверка, не существует ли уже такая связь
            if User_Project.objects.filter(project=project, user=user).exists():
                return Response(
                    {"message": "Пользователь уже добавлен в этот проект"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Создание связи пользователя с проектом
            user_project = User_Project.objects.create(
                project=project,
                user=user,
                isnew=isnew
            )
            # Формирование успешного ответа
            return Response(
                {
                    "success": True,
                    "id": user_project.id,
                    "project_id": user_project.project.id,
                    "user_id": user_project.user.id,
                    "isnew": user_project.isnew,
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя в проект: {str(e)}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "message": "Внутренняя ошибка сервера",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PersonalProjectsView(APIView):
    @swagger_auto_schema(
        operation_description="Получение личных проектов пользователя (где он создатель)",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="ID пользователя",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Список личных проектов пользователя",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'dateofcreation': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'creator_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'deadline': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Не указан ID пользователя",
            404: "Пользователь не найден",
            500: "Внутренняя ошибка сервера"
        }
    )
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response(
                    {"error": "Необходимо указать user_id", "message": "Ошибка валидации."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден", "message": "Ошибка валидации."},
                    status=status.HTTP_404_NOT_FOUND
                )
            # Получаем проекты, где пользователь является создателем (через модель Project)
            projects = Project.objects.filter(creator_id=user_id)
            projects_data = [{
                'id': project.id,
                'name': project.name,
                'dateofcreation': project.dateofcreation,
                'creator_id': project.creator_id,
                'deadline': project.deadline,
                'description': project.description,
            } for project in projects]
            return Response(
                {
                    "data": projects_data,
                    "message": f"Найдено {len(projects_data)} проектов."
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при получении проектов."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InvitedProjectsView(APIView):
    @swagger_auto_schema(
        operation_description="Получение проектов, куда пользователь приглашен (где он участник, но не создатель)",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="ID пользователя",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Список приглашенных проектов пользователя",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'dateofcreation': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'creator_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'deadline': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Не указан ID пользователя",
            404: "Пользователь не найден",
            500: "Внутренняя ошибка сервера"
        }
    )
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response(
                    {"error": "Необходимо указать user_id", "message": "Ошибка валидации."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден", "message": "Ошибка валидации."},
                    status=status.HTTP_404_NOT_FOUND
                )
            # Получаем ID проектов, где пользователь является создателем
            owned_project_ids = Project.objects.filter(creator_id=user_id).values_list('id', flat=True)
            # Получаем проекты, где пользователь участник, но не создатель
            invited_projects = User_Project.objects.filter(
                user_id=user_id
            ).exclude(
                project_id__in=owned_project_ids
            ).select_related('project')
            projects_data = [{
                'id': up.project.id,
                'name': up.project.name,
                'dateofcreation': up.project.dateofcreation,
                'creator_id': up.project.creator_id,
                'deadline': up.project.deadline,
                'description': up.project.description,
            } for up in invited_projects]
            return Response(
                {
                    "data": projects_data,
                    "message": f"Найдено {len(projects_data)} проектов, где вы являетесь участником."
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при получении списка проектов."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )