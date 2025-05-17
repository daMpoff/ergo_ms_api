from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.db import models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from src.core.utils.database.main import OrderedDictQueryExecutor
from src.core.cms.adp.queries import (
    get_sections_and_tasks,add_new_section,add_new_task
)
from src.core.utils.base.base_views import BaseAPIView
import psycopg2
from django.db import connection
from src.external.crm.models import Section,Task

# Создавайте свои представления здесь
class SectionTaskView(APIView):
    @swagger_auto_schema(
        operation_description="Получение всех разделов и их задач с подзадачами",
        responses={
            200: "Список разделов и их задач.",
            400: "Ошибка при выполнении запроса.",
            500: "Внутренняя ошибка сервера."
        }
    )
    def get(self, request):
        try:
            project_id = request.GET.get('project_id')
            
            # Фильтрация разделов
            filter_conditions = {}
            if project_id:
                filter_conditions['project_id'] = project_id

            sections = Section.objects.filter(**filter_conditions).select_related('project')

            sections_data = []
            for section in sections:
                # Получаем родительские задачи (где parenttask_id равен id)
                parent_tasks = Task.objects.filter(
                    section=section,
                    parenttask_id=models.F('id')
                ).select_related('user')

                cards = []
                for task in parent_tasks:
                    # Получаем подзадачи для этой задачи (исключая саму родительскую задачу)
                    subtasks = Task.objects.filter(
                        parenttask_id=task.id
                    ).exclude(  # Добавляем exclude чтобы исключить родительскую задачу
                        id=task.id
                    ).values(
                        'id', 'text', 'priority', 'description', 
                        'user_id', 'isdone', 'deadline'
                    )
                    
                    card = {
                        'id': task.id,
                        'title': task.text,
                        'priority': task.priority,
                        'description': task.description,
                        'user_id': task.user.id if task.user else None,
                        'parenttask_id': task.parenttask_id,
                        'subtasks': list(subtasks)  # Преобразуем QuerySet в список
                    }
                    cards.append(card)

                section_data = {
                    'id': section.id,
                    'title': section.name,
                    'cards': cards,
                    'project_id': section.project.id,
                }
                sections_data.append(section_data)

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
                                'parenttask_id': openapi.Schema(type=openapi.TYPE_INTEGER),
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
            
            task_data = {
                'text': text,
                'section_id': section_id,
                'description': request.data.get('description'),
                'deadline': request.data.get('deadline'),
                'priority': request.data.get('priority', 0),
                'user_id': request.data.get('user_id'),
                'isdone': request.data.get('isdone', False),
                'dateofcreation': request.data.get('dateofcreation') or timezone.now().isoformat(),
            }
            
            with connection.cursor() as cursor:
                # Создаем задачу и сразу устанавливаем parenttask_id = id
                sql = """
                    INSERT INTO crm_task (
                        text, section_id, description, deadline, priority, 
                        user_id, isdone, dateofcreation, parenttask_id
                    ) VALUES (
                        %(text)s, %(section_id)s, %(description)s, %(deadline)s, 
                        %(priority)s, %(user_id)s, %(isdone)s, %(dateofcreation)s,
                        (SELECT currval(pg_get_serial_sequence('crm_task','id')))
                    )
                    RETURNING id, text, section_id, isdone, dateofcreation, parenttask_id
                """
                cursor.execute(sql, task_data)
                row = cursor.fetchone()
                
                created_task = {
                    'id': row[0],
                    'text': row[1],
                    'section_id': row[2],
                    'isdone': row[3],
                    'dateofcreation': row[4],
                    'parenttask_id': row[5],
                }
            
            return Response(
                {
                    "success": True,
                    "data": created_task,
                    "message": "Задача успешно создана."
                },
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Ошибка при создании задачи."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# views.py
from rest_framework.permissions import IsAuthenticated

from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.db import transaction


class DeleteTaskView(APIView):
    @transaction.atomic
    def delete(self, request, task_id):
        try:
            # Получаем задачу или возвращаем 404
            task = get_object_or_404(Task, id=task_id)
            
            # Проверяем права доступа
            if task.user != request.user:
                return Response(
                    {"error": "Forbidden", "message": "У вас нет прав на удаление этой задачи"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Получаем ID всех подзадач (рекурсивно)
            def get_subtask_ids(parent_id):
                subtasks = Task.objects.filter(parenttask_id=parent_id).values_list('id', flat=True)
                ids = list(subtasks)
                for subtask_id in subtasks:
                    ids.extend(get_subtask_ids(subtask_id))
                return ids
            
            # Собираем все ID для удаления
            task_ids = [task.id] + get_subtask_ids(task.id)
            
            # Удаляем задачи (каскадное удаление настроено в моделях)
            Task.objects.filter(id__in=task_ids).delete()
            
            return Response(
                {"success": True, "message": "Задача и подзадачи успешно удалены"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Внутренняя ошибка сервера при удалении задачи"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )