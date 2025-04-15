from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.core.utils.database.main import OrderedDictQueryExecutor
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import (Group, Permission)
from src.core.utils.base.base_views import BaseAPIView
from src.core.cms.queries import (get_users_permissions, get_users_group, get_users_group_permissions, get_group_permissions)

from rest_framework.request import Request

class GetUserPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав пользователя.",
        responses={
            200: "Права пользователя получены",
            401: "Не удалось получить права пользователя"
        }
    )
    def get(self, request: Request):
        id = request.user.id
        result = OrderedDictQueryExecutor.fetchall(
            get_users_permissions,
            id,
        )
        result = [dict(item) for item in result]
        result.append({'is_super': request.user.is_superuser})
        return Response(
            result,
            status=status.HTTP_200_OK
        )
    
class GetUserGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение групп пользователя.",
        responses={
            200: "группы пользователя получены",
            401: "Не удалось получить группы пользователя"
        }
    )
    def get(self, request: Request):
        id = request.user.id
        result = OrderedDictQueryExecutor.fetchall(
            get_users_group,
            id,
        )
        result = [dict(item) for item in result]
        result.append({'is_super': request.user.is_superuser})
        return Response(
            result,
            status=status.HTTP_200_OK
        )
    
class GetUserGroupPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав пользователя через его группу.",
        responses={
            200: "Права пользователя получены",
            401: "Не удалось получить права пользователя"
        }

    )
    def get(self, request: Request):
        id = request.user.id
        result = OrderedDictQueryExecutor.fetchall(
            get_users_group_permissions,
            id,
        )
        result = [dict(item) for item in result]
        result.append({'is_super': request.user.is_superuser})
        return Response(
            result,
            status=status.HTTP_200_OK
        )
class GetGroupPermissions(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Получение прав группы.",
        responses={
            200: "Права группы получены",
            401: "Не удалось получить права группы"
        },
        manual_parameters=[openapi.Parameter('group_name',openapi.IN_QUERY, description='имя группы', type= openapi.TYPE_STRING ),]
    )

    def get(self, request: Request):
        name = request.query_params.get('group_name')
        print(name)
        result = OrderedDictQueryExecutor.fetchall(
            get_group_permissions,
            name,
        )
        return Response(
            result,
            status=status.HTTP_200_OK
        )


class AddGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Добавление группы",
        responses={
            200: "Группа добавлена",
            401: "Не удалось добавить группу"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'group_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя группы'
                ),
            }
        )
    )
    def post(self, request: Request):
        Group.objects.create(name= request.data['group_name'])
        return Response(
            status=status.HTTP_200_OK
        )
    
class AddPermission(BaseAPIView):
     permission_classes = [IsAuthenticated]
     @swagger_auto_schema(
        operation_description="Добавление права",
        responses={
            200: "право добавлено",
            401: "Не удалось добавить право"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя права'
                ),
                'code_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Название кода'
                ),
            }
        )
    )
     def post(self, request: Request):
        content_type = ContentType.objects.get_or_create(app_label='cms', model='none')
        Permission.objects.create(name=request.data['permission_name'], content_type_id =content_type[0].id, codename =request.data['code_name'])
        return Response(
            status=status.HTTP_200_OK
        )
     
class DeleteGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="удаление группы",
        responses={
            200: "Группа удалена",
            401: "Не удалось удалить группу"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'group_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя группы'
                ),
            }
        )
    )
    def delete(self, request: Request):
        nameg = request.data['group_name']
        group = Group.objects.get(name = nameg )
        group.delete()
        return Response(
            status=status.HTTP_200_OK
        )

class DeletePermission(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="удаление права",
        responses={
            200: "право удалена",
            401: "Не удалось удалить право"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя права'
                ),
            }
        )
    )
    def delete(self, request: Request):
        namep = request.data['permission_name']
        permission = Permission.objects.get(name = namep )
        permission.delete()
        return Response(
            status=status.HTTP_200_OK
        )


class UpdateGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="обновление группы",
        responses={
            200: "Группа обновлена",
            401: "Не удалось обновить группу"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'group_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя группы'
                ),
                'new_group_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Новое имя группы'
                ),
            }
        )
    )
    def put(self, request: Request):
        nameg = request.data['group_name']
        group = Group.objects.get(name = nameg )
        group.name = request.data['new_group_name']
        group.save()
        return Response(
            status=status.HTTP_200_OK
        )

class UpdatePermissionName(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="обновление имени права",
        responses={
            200: "имя права обновлено",
            401: "Не удалось обновить имя права"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя группы'
                ),
                'new_permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Новое имя группы'
                ),
            }
        )
    )
    def patch(self, request: Request):
        namep = request.data['permission_name']
        permission = Permission.objects.get(name = namep )
        permission.name = request.data['new_permission_name']
        permission.save()
        return Response(
            status=status.HTTP_200_OK
        )
class UpdatePermissionCodeName(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="обновление кода права",
        responses={
            200: "код права обновлен",
            401: "Не удалось обновить код права"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя группы'
                ),
                'new_permission_codename': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Новое имя группы'
                ),
            }
        )
    )
    def patch(self, request: Request):
        namep = request.data['permission_name']
        permission = Permission.objects.get(name = namep )
        permission.codename = request.data['new_permission_codename']
        permission.save()
        return Response(
            status=status.HTTP_200_OK
        )