from datetime import datetime, timedelta
from rest_framework.permissions import IsAuthenticated
from src.core.utils.base.base_views import BaseAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone

from src.modules.cities_expansion.models import FileUpload
from src.modules.cities_expansion.models import Group
from src.modules.cities_expansion.models import FileGroup
from src.modules.cities_expansion.models import Task, TaskResult

from src.modules.cities_expansion.geoanalyzer.models import GroupCoords

from src.modules.cities_expansion.geoanalyzer.methods import parse_coordinate
from src.modules.cities_expansion.geoanalyzer.methods import process_map_group

class UploadMaps(BaseAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @swagger_auto_schema(
        operation_description="Загрузка и обработка карт города",
        manual_parameters=[
            openapi.Parameter(
                'name',
                openapi.IN_FORM,
                description="Название группы карт (например, 'Хабаровск')",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'coords-string',
                openapi.IN_FORM,
                description="Координаты в формате чч°мм'сс\"N, чч°мм'сс\"E → чч°мм'сс\"N, чч°мм'сс\"E",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'city_map',
                openapi.IN_FORM,
                description="Карта города (PNG, обязательное)",
                type=openapi.TYPE_FILE,
                required=True
            ),
            openapi.Parameter(
                'buildings_map',
                openapi.IN_FORM,
                description="Карта зданий (PNG, обязательное)",
                type=openapi.TYPE_FILE,
                required=True
            ),
            openapi.Parameter(
                'railways_map',
                openapi.IN_FORM,
                description="Карта железных дорог (PNG, опционально)",
                type=openapi.TYPE_FILE,
                required=False
            )
        ],
        responses={
            201: openapi.Response(
                description="Карты успешно загружены",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'upload_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'files': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'city_map': openapi.Schema(type=openapi.TYPE_STRING),
                                'buildings_map': openapi.Schema(type=openapi.TYPE_STRING),
                                'railways_map': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Может отсутствовать"
                                )
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Ошибка валидации",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(
                description="Не авторизован"
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            # Получаем обязательные файлы
            city_map = request.FILES.get('city_map')
            buildings_map = request.FILES.get('buildings_map')
            group_name = request.POST.get('name').strip()
            coords_string = request.POST.get('coords-string').strip()
            
            if len(group_name) < 4:
                return Response(
                    {'error': 'Название группы должно быть не меньше четырёх символов'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            parts = coords_string.split(' → ')
            if len(parts) != 2:
                return Response(
                    {'error': 'Координаты в неправильном формате'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            UPPER_LEFT_COORD = parse_coordinate(parts[0])
            DOWN_RIGHT_COORD = parse_coordinate(parts[1])

            if len(UPPER_LEFT_COORD) != 2 or len(DOWN_RIGHT_COORD) != 2:
                return Response(
                    {'error': 'Координаты в неправильном формате'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not city_map or not buildings_map:
                return Response(
                    {'error': 'Необходимо загрузить карту города и карту зданий'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем тип файлов
            if not city_map.name.lower().endswith('.png') or not buildings_map.name.lower().endswith('.png'):
                return Response(
                    {'error': 'Файлы должны быть в формате PNG'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Обработка опциональной карты железных дорог
            railways_map = request.FILES.get('railways_map', None)
            if railways_map and not railways_map.name.lower().endswith('.png'):
                return Response(
                    {'error': 'Файл карты железных дорог должен быть в формате PNG'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Сохраняем файлы
            def save_file(file, name):
                if not file:
                    return None
                upload = FileUpload()
                upload.filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                upload.user = request.user
                upload.date = datetime.now()
                upload.file.save(upload.filename, file)
                upload.save()
                return upload
            
            saved_files = {
                'city_map': save_file(city_map, 'city_map'),
                'buildings_map': save_file(buildings_map, 'buildings_map')
            }

            if railways_map is not None:
                saved_files['railways_map'] = save_file(railways_map, 'railways_map')

            upload_group = Group(name=group_name, user=request.user)
            upload_group.save()

            fg_coords = GroupCoords(group=upload_group)
            fg_coords.upper_left_latitude = UPPER_LEFT_COORD[0]
            fg_coords.upper_left_longitude = UPPER_LEFT_COORD[1]
            fg_coords.down_right_latitude = DOWN_RIGHT_COORD[0]
            fg_coords.down_right_longitude = DOWN_RIGHT_COORD[1]
            fg_coords.save()

            for k,v in saved_files.items():
                file_group = FileGroup()
                file_group.upload = v
                file_group.group = upload_group
                file_group.save()

            return Response({
                'success': True,
                'message': 'Карты успешно загружены',
                'files': {k: v.filename for k, v in saved_files.items() if v is not None}
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PerformAnalysis(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        Запускает анализ группы файлов. 
        Для успешного анализа в группе должны присутствовать файлы с префиксами 'city_map' и 'buildings_map'.
        """,
        manual_parameters=[
            openapi.Parameter(
                'group_id',
                openapi.IN_QUERY,
                description="ID группы файлов для анализа",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'k',
                openapi.IN_QUERY,
                description="Количество кластеров для разбиения города",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Задача на анализ успешно запущена",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Сообщение об успешном запуске задачи"
                        ),
                        'task_id': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="ID созданной задачи для отслеживания статуса"
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Неверный запрос",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Описание ошибки"
                        )
                    }
                ),
                examples={
                    "application/json": {
                        "error": "Группа файлов не удовлетворяет требованиям (нет городской карты или карты зданий)"
                    }
                }
            ),
            404: openapi.Response(
                description="Группа не найдена",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Сообщение о том, что группа не найдена"
                        )
                    }
                )
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Описание ошибки"
                        )
                    }
                )
            )
        },
        security=[{"Bearer": []}]
    )
    def get(self, request, *args, **kwargs):
        try:
            group_id = request.GET.get('group_id')
            group_obj = Group.objects.get(id=group_id)

            k = int(request.GET.get('k'))

            files: dict[str] = {}

            group_files = FileGroup.objects.filter(group=group_obj)

            for f in group_files:
                files[f.upload.filename] = f.upload.file.name
            

            has_city_map = any([filename.startswith('city_map') for filename in files])
            has_buildings_map = any([filename.startswith('buildings_map') for filename in files])
            if not has_city_map or not has_buildings_map:
                return Response(
                    {'error': 'Группа файлов не удовлетворяет требованиям (нет городской карты или карты зданий)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if k < 2:
                return Response(
                    {'error': 'Нельзя произвести анализ с количеством кластеров меньше двух.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            coords = GroupCoords.objects.get(group=group_obj)
            
            task = Task()
            task.date = datetime.now()
            task.user = request.user
            task.status = Task.StatusChoices.RUNNING
            task.save()

            process_map_group.delay(task.task_id, files, coords.id, k)

            return Response(
                {
                    'success': f'Задача по анализу {group_obj.name} запустилась',
                    'task_id': task.task_id
                },
                status=status.HTTP_200_OK
            )
        except Group.DoesNotExist:
            return Response(
                {'error': 'Группа не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TaskStatus(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        Получает статус задачи по её ID.
        Возвращает текущее состояние задачи и, если задача завершена успешно, её результаты.
        """,
        manual_parameters=[
            openapi.Parameter(
                'task_id',
                openapi.IN_QUERY,
                description="ID задачи для проверки статуса",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Информация о задаче",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'task_id': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="ID задачи"
                        ),
                        'status': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            enum=[choice.value for choice in Task.StatusChoices],
                            description="Текущий статус задачи"
                        ),
                        'status_description': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Детальное описание статуса задачи",
                            nullable=True
                        ),
                        'date': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_DATETIME,
                            description="Дата и время создания задачи"
                        ),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Результаты выполнения задачи (только если статус FINISHED)",
                            nullable=True,
                            additional_properties=True
                        )
                    }
                ),
                examples={
                    "application/json": {
                        "task_id": 123,
                        "status": "FINISHED",
                        "status_description": "Задача успешно завершена",
                        "date": "2023-05-15T14:30:00Z",
                        "result": {"buildings_count": 42, "area": 12500}
                    }
                }
            ),
            404: openapi.Response(
                description="Задача не найдена",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Сообщение об ошибке"
                        )
                    }
                )
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Описание ошибки"
                        )
                    }
                )
            )
        },
        security=[{"Bearer": []}]
    )
    def get(self, request, *args, **kwargs):
        try:
            task_id = request.GET.get('task_id')
            task = Task.objects.get(task_id=task_id, user=request.user)

            response_data = {
                'task_id': task.task_id,
                'status': task.status,
                'status_description': task.status_description,
                'date': task.date
            }
            
            if task.status == Task.StatusChoices.FINISHED:
                try:
                    task_result = TaskResult.objects.get(task=task)
                    response_data['result'] = task_result.result
                except TaskResult.DoesNotExist:
                    pass
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Task.DoesNotExist:
            return Response(
                {'error': 'Задача не найдена или у вас нет к ней доступа'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )