from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.urls import reverse
from django.http import FileResponse

from src.modules.cities_expansion.models import Location, LocationType, CountryCodeAdjacent, BoundingBox
from src.modules.cities_expansion.serializers import LocationSerializer, CountryCodeSerializer, BoundingBoxSerializer
from src.modules.cities_expansion.models import FileUpload, Group, FileGroup
from src.modules.cities_expansion.models import Task, TaskResult

from src.modules.cities_expansion.geoanalyzer.models import GroupCoords

from src.core.utils.base.base_views import BaseAPIView

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class CitiesView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о доступных городах",
        responses={
            200: openapi.Response(
                description="Список городов",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'cities': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'location_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'location_type': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'location_type_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                                        }
                                    )
                                }
                            )
                        )
                    }
                )
            )
        }
    )

    def get(self, request, *args, **kwargs):
        cities = Location.objects.filter(location_type__name=LocationType.LocationTypeChoices.CITY.value)
        serializer = LocationSerializer(cities, many=True)
        data = {"cities": serializer.data}
        return Response(data, status=status.HTTP_200_OK) 
    
class CountriesView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о доступных странах",
        responses={
            200: openapi.Response(
                description="Список стран",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'countries': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'location_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'location_type': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'location_type_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                                        }
                                    )
                                }
                            )
                        )
                    }
                )
            )
        }
    )

    def get(self, request, *args, **kwargs):
        countries = Location.objects.filter(location_type__name=LocationType.LocationTypeChoices.COUNTRY.value)
        serializer = LocationSerializer(countries, many=True)
        data = {"countries": serializer.data}
        return Response(data, status=status.HTTP_200_OK)

class CountryCodesView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о доступных кодах стран",
        responses={
            200: openapi.Response(
                description="Список кодов стран",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'country_codes': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'location_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'country_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'a2_code': openapi.Schema(type=openapi.TYPE_STRING),
                                    'a3_code': openapi.Schema(type=openapi.TYPE_STRING),
                                    'numeric': openapi.Schema(type=openapi.TYPE_INTEGER)
                                }
                            )
                        )
                    }
                )
            )
        }
    )

    def get(self, request, *args, **kwargs):
        country_codes = CountryCodeAdjacent.objects.all()
        serializer = CountryCodeSerializer(country_codes, many=True)
        data = {"country_codes": serializer.data}
        return Response(data, status=status.HTTP_200_OK)

class BoundingBoxesView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение информации о доступных ограничивающих прямоугольниках",
        responses={
            200: openapi.Response(
                description="Список ограничивающих прямоугольников",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'bounding_boxes': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'location_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'location_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'location_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'bottom_left_latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'bottom_left_longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'upper_right_latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'upper_right_longitude': openapi.Schema(type=openapi.TYPE_NUMBER)
                                }
                            )
                        )
                    }
                )
            )
        }
    )

    def get(self, request, *args, **kwargs):
        bounding_boxes = BoundingBox.objects.all()
        serializer = BoundingBoxSerializer(bounding_boxes, many=True)
        data = {"bounding_boxes": serializer.data}
        return Response(data, status=status.HTTP_200_OK)

class GetMyGroups(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        Получает группы файлов аутентифицированного пользователя.
        
        Возвращает список групп, в формате:
        - ID группы
        - Название группы
        - Список файлов в группе (каждый файл с ID и названием)
        - Дополнительную информацию о группе (если она есть)
        """,
        responses={
            200: openapi.Response(
                description="Список групп успешно получен",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID группы'),
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название группы'),
                            'files': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                description='Список файлов в группе',
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_STRING, description='ID файла'),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название файла'),
                                    }
                                )
                            ),
                            'details': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                description='Дополнительная информация о группе',
                                properties={
                                    'coords': openapi.Schema(type=openapi.TYPE_STRING, description='Координаты (если это группа изображений карт)'),
                                }
                            )
                        }
                    )
                )
            ),
            401: openapi.Response(
                description="Не авторизован"
            )
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, *args, **kwargs):
        groups = Group.objects.filter(user=request.user)

        result = []
        for g in groups:
            g_result = {'id': g.id, 'name': g.name, 'files': [], 'details': {}}
            files = FileGroup.objects.filter(group=g)
            for f in files:
                g_result['files'].append({'id': f.upload.upload_id, 'name': f.upload.filename})
            
            coords = GroupCoords.objects.filter(group=g).first()

            if coords:
                g_result['details']['coords'] = str(coords)

            result.append(g_result)
        
        return Response(result, status=status.HTTP_200_OK)

class GetFile(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        Загружает файл по указанному ID, если авторизованный пользователь имеет к нему доступ
        
        Необходим ID файла
        """,
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID файла для загрузки'
            )
        ],
        responses={
            200: openapi.Response(
                description="Файл",
                schema=openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Запрашиваемый файл'
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='У вас нет прав доступа к этому файлу'
                        )
                    }
                )
            ),
            404: openapi.Response(
                description="Not Found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='Файл не найден'
                        )
                    }
                )
            ),
            500: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='Error message'
                        )
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, *args, **kwargs):
        try:
            upload_id = int(request.GET.get('id'))
            file_obj = FileUpload.objects.get(upload_id=upload_id)
            
            if file_obj.user != request.user:
                return Response(
                    {'error': 'У вас нет прав доступа к этому файлу'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return FileResponse(file_obj.file.open())
        except FileUpload.DoesNotExist:
            return Response(
                {'error': 'Файл не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeleteGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        Удаляет группу и все её файлы
        
        Требования:
        - Пользователь авторизован
        - Пользователь владелец группы
        - Необходимо предоставить ID группы
        
        Данная операция:
        1. Удалит все файлы, ассоциированные с группой
        2. Удалит саму группу
        """,
        responses={
            200: openapi.Response(
                description="Группа и файлы успешно удалены",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='Группа и файлы были удалены.'
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='Необходим ID группы.'
                        )
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='У вас нет разрешений для удаления этой группы.'
                        )
                    }
                )
            ),
            404: openapi.Response(
                description="Not Found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example='Group not found'
                        )
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, group_id, *args, **kwargs):
        if not group_id:
            return Response({'error': 'Необходим ID группы.'}, status=status.HTTP_400_BAD_REQUEST)

        group = get_object_or_404(Group, id=group_id)

        # Проверка, что пользователь владелец группы
        if group.user != request.user:
            return Response({'error': 'У вас нет разрешений для удаления этой группы.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Получаем все связи FileGroup и удаляем соответствующие файлы
        file_groups = FileGroup.objects.filter(group=group)
        for file_group in file_groups:
            file_upload = file_group.upload
            file_upload.delete()  # Это удалит файл с диска и запись из базы

        group.delete()

        return Response({'message': 'Группа и файлы были удалены.'},
                        status=status.HTTP_200_OK)

class GetMyTasks(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""
        Получает задачи авторизованного пользователя
        
        Возвращает список задач, в формате:
        - ID задачи
        - Дата запуска задачи
        - Статус задачи (общий и детальный)
        """,
        responses={
            200: openapi.Response(
                description="Список задач успешно получен",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID задачи'),
                            'date': openapi.Schema(type=openapi.TYPE_STRING, description='Дата запуска задачи'),
                            'status': openapi.Schema(type=openapi.TYPE_STRING, description='Статус задачи'),
                            'status_description': openapi.Schema(type=openapi.TYPE_STRING, description='Расширенный статус задачи')
                        }
                    )
                )
            ),
            401: openapi.Response(
                description="Не авторизован"
            )
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, *args, **kwargs):
        tasks = Task.objects.filter(user=request.user)

        result = []
        for t in tasks:

            if t.status == Task.StatusChoices.RUNNING and t.date < timezone.now() - timedelta(hours=4):
                t.status = Task.StatusChoices.FAILED
                t.status_description = "Истекло время выполнения задачи"
                t.save()

            t_result = {'id': t.task_id, 'date': t.date.isoformat(), 'status': t.status, 'status_description': t.status_description}

            result.append(t_result)
        
        return Response(result, status=status.HTTP_200_OK)