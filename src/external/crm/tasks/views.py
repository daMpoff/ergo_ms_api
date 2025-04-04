from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from src.core.utils.database.main import OrderedDictQueryExecutor
from src.core.cms.adp.queries import (
    get_sections_and_tasks,add_new_section,add_new_task
)
from src.core.utils.base.base_views import BaseAPIView
import psycopg2
from django.db import connection
from src.external.crm.models import Section

# Создавайте свои представления здесь
class SectionTaskView(APIView):
    @swagger_auto_schema(
        operation_description="Получение всех разделов и их задач",
        responses={
            200: "Список разделов и их задач.",
            400: "Ошибка при выполнении запроса.",
            500: "Внутренняя ошибка сервера."
        }
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                sql, params = get_sections_and_tasks()
                cursor.execute(sql, params)
                rows = cursor.fetchall()

                sections_data = []
                for row in rows:
                    section_id = row[0]
                    section_title = row[1]
                    tasks = row[3]  # JSON массив задач

                    # Преобразуем задачи в нужный формат
                    cards = []
                    for task in tasks:
                        card = {
                            'id': task['id'],
                            'title': task['text'],
                            'priority': task['priority'],  # Используем приоритет как тег
                            'image': None,  # По умолчанию изображение отсутствует
                            'attachments': 0,  # По умолчанию вложений нет
                            'comments': task['description'],  # По умолчанию комментариев нет
                            'user_id':task['user_id'],
                        }
                        cards.append(card)

                    # Создаем раздел с карточками
                    section = {
                        'id': section_id,
                        'title': section_title,
                        'cards': cards,
                    }
                    sections_data.append(section)

            return Response(
                {"data": sections_data, "message": "Разделы и задачи успешно получены."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при получении данных."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SectionCreateView(APIView):
    @swagger_auto_schema(
        operation_description="Добавление нового раздела",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['section_name', 'project_id'],
            properties={
                'section_name': openapi.Schema(type=openapi.TYPE_STRING, description='Название раздела'),
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID проекта'),
            },
        ),
        responses={
            201: openapi.Response(
                description="Раздел успешно создан",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Неверные входные данные",
            500: "Внутренняя ошибка сервера"
        }
    )
    def post(self, request):
        try:
            section_name = request.data.get('section_name')
            project_id = request.data.get('project_id')
            
            if not section_name or not project_id:
                return Response(
                    {"error": "Необходимо указать section_name и project_id", "message": "Ошибка валидации."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Создаем раздел через ORM (id будет автоматически сгенерирован)
            section = Section.objects.create(
                name=section_name,
                project_id=project_id
            )
            
            # Формируем ответ с созданным разделом
            created_section = {
                'id': section.id,  # автоинкрементное поле
                'name': section.name,
                'project_id': section.project_id,
            }
            
            return Response(
                {
                    "data": created_section,
                    "message": "Раздел успешно создан."
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при создании раздела."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class TaskCreateView(APIView):
    @swagger_auto_schema(
        operation_description="Добавление новой задачи",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text', 'section_id'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='Текст задачи'),
                'section_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID раздела'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание задачи', default=None),
                'deadline': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Срок выполнения', default=None),
                'priority': openapi.Schema(type=openapi.TYPE_INTEGER, description='Приоритет задачи', default=0),
                'parenttask_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID родительской задачи', default=None),
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID пользователя', default=None),
                'isdone': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус выполнения задачи', default=False),
                'dateofcreation': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Дата создания задачи', default=None),
            },
        ),
        responses={
            201: openapi.Response(
                description="Задача успешно создана",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'text': openapi.Schema(type=openapi.TYPE_STRING),
                                'section_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'isdone': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'dateofcreation': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            }
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Неверные входные данные",
            500: "Внутренняя ошибка сервера"
        }
    )
    def post(self, request):
        try:
            text = request.data.get('text')
            section_id = request.data.get('section_id')
            
            if not text or not section_id:
                return Response(
                    {"error": "Необходимо указать text и section_id", "message": "Ошибка валидации."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Подготавливаем данные задачи
            task_data = {
                'text': text,
                'section_id': section_id,
                'description': request.data.get('description'),
                'deadline': request.data.get('deadline'),
                'priority': request.data.get('priority', 0),
                'parenttask_id': request.data.get('parenttask_id'),
                'user_id': request.data.get('user_id'),
                'isdone': request.data.get('isdone', False),
                'dateofcreation': request.data.get('dateofcreation') or timezone.now().isoformat(),
            }
            
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO crm_task (
                        text, section_id, description, deadline, priority, 
                        parenttask_id, user_id, isdone, dateofcreation
                    ) VALUES (
                        %(text)s, %(section_id)s, %(description)s, %(deadline)s, 
                        %(priority)s, %(parenttask_id)s, %(user_id)s, %(isdone)s, %(dateofcreation)s
                    ) RETURNING id, text, section_id, isdone, dateofcreation
                """
                cursor.execute(sql, task_data)
                row = cursor.fetchone()
                
                created_task = {
                    'id': row[0],
                    'text': row[1],
                    'section_id': row[2],
                    'isdone': row[3],
                    'dateofcreation': row[4],
                }
                
            return Response(
                {
                    "data": created_task,
                    "message": "Задача успешно создана."
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": str(e), "message": "Ошибка при создании задачи."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )