from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.external.crm.models import Project, User_Project
from django.contrib.auth import get_user_model

User = get_user_model()

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
    @swagger_auto_schema(
        operation_description="Добавление нового проекта",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['project_name', 'creator_id'],
            properties={
                'project_name': openapi.Schema(type=openapi.TYPE_STRING, description='Название проекта'),
                'creator_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID создателя проекта'),
            },
        ),
        responses={
            201: openapi.Response(
                description="Проект успешно создан",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'dateofcreation': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                'creator_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Неверные входные данные",
            404: "Пользователь не найден",
            500: "Внутренняя ошибка сервера"
        }
    )
    def post(self, request):
        try:
            project_name = request.data.get('project_name')
            creator_id = request.data.get('creator_id')
            
            if not project_name or not creator_id:
                return Response(
                    {"error": "Необходимо указать project_name и creator_id", "message": "Ошибка валидации."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                creator = User.objects.get(pk=creator_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден", "message": "Ошибка валидации."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            project = Project.objects.create(
                name=project_name,
                creator=creator
            )
            
            created_project = {
                'id': project.id,
                'name': project.name,
                'dateofcreation': project.dateofcreation,
                'creator_id': project.creator_id,
            }
            
            return Response(
                {
                    "data": created_project,
                    "message": "Проект успешно создан."
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при создании проекта."},
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