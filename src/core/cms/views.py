from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import (Group, Permission, User)
from src.core.utils.base.base_views import BaseAPIView
from src.core.cms.models import (ExpandedPermission,Accession, GroupCategory, ExpandedGroup, PermissionMark, Accession)
from rest_framework.request import Request
from src.core.cms.commands import GetUserExpandedPermissions
#Управление категорями групп
class AddGroupCategory(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Добавление категории группы",
        responses={
            200: "Категория добавлена",
            401: "Пользователь не авторизован",
            403: "Нет доступа",
            400: "Неверный данные"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя категории'
                ),
                'create_admin_group': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Создать группу администраторов'
                )
            }
        )
    )
    def post(self, request: Request):
        if(request.user.is_superuser):
            cats = GroupCategory.objects.all()
            for cat in cats:
                if cat.name == request.data['category_name']:
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )
            catg = GroupCategory.objects.create(name = request.data['category_name'])
            ct = ContentType.objects.get_or_create(app_label='cms', model='none')
            pm = PermissionMark.objects.get(id = 9)
            p = Permission.objects.create(codename ='Admin of Category '+ request.data['category_name'], name = request.data['category_name'] + ' redact', content_type = ct[0])
            exp =ExpandedPermission.objects.create(permission = p, group_category = catg, permission_mark = pm)
            Accession.objects.create(typeaccession = 'AdminPanelAccession', path = 'admin', component_id = 'admin_panel', permission = exp)
            
            if request.data['create_admin_group']:
                g =Group.objects.create(name = request.data['category_name'] + ' admin')
                g.permissions.add(p)
                ExpandedGroup.objects.create(group = g, category = catg, level = 10)
            return Response(
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status= status.HTTP_403_FORBIDDEN
            )
class GetGroupCategories(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="получение категорий групп",
        responses={
            200: "Категории получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
    )
    def get(self, request: Request):
        if(request.user.is_superuser):
            categories = GroupCategory.objects.all()
            cats = []
            for cat in categories:
                cats.append({"id": cat.id, "name": cat.name})
            result = {"categories": cats}
            return Response(
                result,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status= status.HTTP_403_FORBIDDEN
            )
class ChangeGroupCategory(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Изменение категории группы",
        responses={
            200: "Категория изменена",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя категории'
                ),
                'new_category_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Новое имя категории'
                )
            }
        )
    )
    def put(self, request: Request):
        if(request.user.is_superuser):
            catg = GroupCategory.objects.get(name = request.data['category_name'])
            catg.name = request.data['new_category_name']
            catg.save()
            return Response(
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class DeleteGroupCategory(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Удаление категории группы",
        responses={
            200: "Категория удалена",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя категории'
                )
            }
        )
    )
    def delete(self, request: Request):
        if(request.user.is_superuser):
            catg = GroupCategory.objects.get(name = request.data['category_name'])
            eg = ExpandedGroup.objects.filter(category = catg)
            for e in eg:
                g = e.group
                g.delete()
                e.delete()
            exps = ExpandedPermission.objects.filter(group_category = catg)
            for exp in exps:
                accession = Accession.objects.get(permission = exp)
                accession.delete()
                permission = exp.permission
                permission.delete()
                exp.delete()
            catg.delete()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
#Управление группами
class AddGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Добавление группы",
        responses={
            200: "Группа добавлена",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'group_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя группы'
                ),
                'level': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Уровень группы'
                ),
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Название категории группы'
                )
            }
        )
    )
    def post(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 & exp.group_category.name == request.data['category_name']:
                access = True
                break
        if(request.user.is_superuser | access):
            catg = GroupCategory.objects.get(name = request.data['category_name'])
            g = Group.objects.create(name= request.data['group_name'])
            ExpandedGroup.objects.create(group=g, category = catg, level = request.data['level'])
            return Response(
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class ChangeGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="обновление группы",
        responses={
            200: "Группа обновлена",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
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
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Название категории группы'
                ),
                'level': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Уровень группы'
                )
            }
        )
    )
    def put(self, request: Request):
        g = Group.objects.get(name = request.data['group_name'])
        eg = ExpandedGroup.objects.get(group = g)
        access = False
        groups = request.user.groups.all()
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 & exp.group_category.name == eg.category.name:
                access = True
                break
        if(request.user.is_superuser | access):
            nameg = request.data['group_name']
            group = Group.objects.get(name = nameg )
            if (request.data['new_group_name'] != '') & (request.data['new_group_name'] != group.name):
                group.name = request.data['new_group_name']
            eg = ExpandedGroup.objects.get(group = group)
            if (request.data['category_name'] != '') & (request.data['category_name'] != eg.category.name):
                eg.category = GroupCategory.objects.get(name = request.data['category_name'])
            if (request.data['level'] != '') & (request.data['level'] != eg.level):
                eg.level = request.data['level']
            eg.save()
            group.save()
            return Response(
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
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
        g = Group.objects.get(name = request.data['group_name'])
        eg = ExpandedGroup.objects.get(group = g)
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 & exp.group_category.name == eg.category.name:
                access = True
                break
        if(request.user.is_superuser | access):
            nameg = request.data['group_name']
            group = Group.objects.get(name = nameg )
            eg = ExpandedGroup.objects.get(group = group.id)
            eg.delete()
            group.delete()
            return Response(
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class GetUserGroups(BaseAPIView):    
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение групп пользователя.",
        responses={
            200: "группы пользователя получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        }
    )
    def get(self, request: Request):
            user = request.user
            groups = user.groups.all()
            groups_names =[]
            for group in groups:
                groups_names.append(group.name)
            result = {"groups":groups_names}
            return Response(
                result,
                status=status.HTTP_200_OK
            )
class GetGroups(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение групп.",
        responses = {
            200: "группы получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        }
    )
    def get(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
                break
        if(request.user.is_superuser | access):
            groups = Group.objects.all()
            groups_list =[]
            if(request.user.is_superuser):
               for group in groups:
                    expanded_group = ExpandedGroup.objects.get(group_id = group.id)
                    permissions = group.permissions.all()
                    permissions_list = []
                    for permission in permissions:
                        permissions_list.append(permission.name)
                    tmpres = {'id':group.id, 'name':group.name, 'category':expanded_group.category.name, 'level':expanded_group.level, 'permissions':permissions_list}
                    groups_list.append(tmpres)
            else:
                cat_list=[]
                for exp in exps:
                    if exp.permission_mark.id == 9:
                        cat_list.append(exp.group_category.name)
                for cat in cat_list:                
                    for group in groups:
                        if group.category.name == cat:
                            expanded_group = ExpandedGroup.objects.get(group_id = group.id)
                            permissions = group.permissions.all()
                            permissions_list = []
                            for permission in permissions:
                                permissions_list.append(permission.name)
                            tmpres = {'id':group.id, 'name':group.name, 'category':expanded_group.category.name, 'level':expanded_group.level, 'permissions':permissions_list}
                            groups_list.append(tmpres)
            result = {"groups":groups_list}
            return Response(
                result,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class AddGroupPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Добавление прав группе",
        responses={
            200: "Права группе добавлены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'group_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя группы'),
                'permissions_name': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Items(type=openapi.TYPE_STRING), description='Имя права')
            }
        )
    )
    def post(self, request: Request):
        access = False
        group = Group.objects.get(name = request.data['group_name'])
        exp_group = ExpandedGroup.objects.get(group=group)
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 and exp.group_category==exp_group.group_category:
                access = True
                break
        if(access or request.user.is_superuser):
            for permission_name in request.data['permissions_name']:
                permission = Permission.objects.get(name = permission_name)
                exp_permission = ExpandedPermission.objects.get(permission=permission)
                if(exp_permission.group_category == exp_group.group_category):
                    group.permissions.add(permission)
                else:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
            group.save()
            return Response(status=status.HTTP_200_OK) 
class RemoveGroupPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Удаление прав группе",
        responses={
            200: "Права группе удалены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'group_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя группы'),
                'permissions_name': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Items(type=openapi.TYPE_STRING), description='Имя права')
            }
        )
    )
    def delete(self, request: Request):
        access = False
        group = Group.objects.get(name = request.data['group_name'])
        exp_group = ExpandedGroup.objects.get(group=group)
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 and exp.group_category==exp_group.group_category:
                access = True
                break
        if(access or request.user.is_superuser):
            for permission_name in request.data['permissions_name']:
                permission = Permission.objects.get(name = permission_name)
                exp_permission = ExpandedPermission.objects.get(permission=permission)
                if(exp_permission.group_category == exp_group.group_category):
                    group.permissions.remove(permission)
                else:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
            group.save()
            return Response(status=status.HTTP_200_OK)
#Управление правами
class GetPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав.",
        responses={
            200: "Права получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        }
    )
    def get(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
                break
        if(request.user.is_superuser | access):
            ExpandedPermissions = ExpandedPermission.objects.all()
            if(request.user.is_superuser):
                permissions_list = []
                for expperm in ExpandedPermissions:
                    permission = expperm.permission
                    accession = Accession.objects.get(permission = expperm)
                    permissions_list.append({'id':permission.id, 'name':permission.name,
                    'permission_mark':expperm.permission_mark.id, 'category_name':expperm.group_category.name, 'accession_type':accession.typeaccession,
                    'path':accession.path, 'component_id':accession.component_id})
                result = {"permissions":permissions_list}
            else:
                cat_list=[]
                for exp in exps:
                    if exp.permission_mark.id == 9:
                        cat_list.append(exp.group_category.name)
                for cat in cat_list:                
                    for expperm in ExpandedPermissions:
                        if expperm.category.name == cat:
                            permission = expperm.permission
                            accession = Accession.objects.get(permission = expperm)
                            permissions_list.append({'id':permission.id, 'name':permission.name, 'code_name':permission.codename,
                            'permission_mark':expperm.permission_mark.id, 'category_name':expperm.group_category.name, 'accession_type':accession.typeaccession,
                            'path':accession.path, 'component_id':accession.component_id})
                            result = {"permissions":permissions_list}
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class AddPermission(BaseAPIView):
     permission_classes = [IsAuthenticated]
     @swagger_auto_schema(
        operation_description="Добавление права",
        responses={
            200: "право добавлено",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя права'
                ),
                
                'permission_mark': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Маркер права'
                ),
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Название категории'
                ),
                'accession_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Тип доступа'
                ),
                'path': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Путь доступа'),
                'component_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Идентификатор компонента'
                )
            }
        )
    )
     
     def post(self, request: Request):
        access = False
        perms =[]
        if(request.data['permission_mark'] < 9):
            exps = GetUserExpandedPermissions(request.user)
            for exp in exps:
                if exp.group_category.name == request.data['category_name']:
                    access = True
                    break
            if(access or request.user.is_superuser):
                content_type = ContentType.objects.get_or_create(app_label='cms', model='none')
                categoryy = GroupCategory.objects.get(name = request.data['category_name'])
                pm = PermissionMark.objects.get(id = request.data['permission_mark'])
                permission = Permission.objects.create(name=request.data['permission_name'], content_type_id =content_type[0].id, codename =request.data['permission_name'])
                exp =ExpandedPermission.objects.create(permission = permission,
                permission_mark = pm, group_category = categoryy)
                Accession.objects.create(permission = exp, typeaccession = request.data['accession_type'], path = request.data['path'], component_id = request.data['component_id'])
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
class DeletePermission(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="удаление права",
        responses={
            200: "право удалена",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
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
        expanded_permission = ExpandedPermission.objects.get(permission_id = permission.id)
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 and exp.group_category == expanded_permission.group_category :
                access = True
                break
        if(access or request.user.is_superuser):
            if (expanded_permission.permission_mark.id < 9):
                accs = Accession.objects.get(permission = expanded_permission)
                accs.delete()
                expanded_permission.delete()
                permission.delete()
                return Response(
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class ChangePermission(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="обновление кода права",
        responses={
            200: "код права обновлен",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя права'
                ),
                'new_permission_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Новое имя права'
                ),
                'new_permission_mark': openapi.Schema(
                    type=openapi.TYPE_INTEGER, 
                    description='Новый маркер права'
                ),
                'new_category_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Новая категория права'
                ),
                'accession_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Тип доступа'
                ),
                'path': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Путь доступа'),
                'component_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Идентификатор компонента'
                )
            }
        )
    )
    def put(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 and exp.group_category.name == request.data['new_category_name'] :
                access = True
                break
        if(request.user.is_superuser | access):
            hascategory = False
            for category in GroupCategory.objects.all():
                if(category.name == request.data['new_category_name']):
                    hascategory = True
            if((int(request.data['new_permission_mark']) < 9) & hascategory):
                permission = Permission.objects.get(name = request.data['permission_name'])
                expanded_permission = ExpandedPermission.objects.get(permission = permission)
                category = GroupCategory.objects.get(name = request.data['new_category_name'])
                accs = Accession.objects.get(permission = expanded_permission)
                if(permission.name != request.data['new_permission_name']):
                    permission.name = request.data['new_permission_name']
                    permission.codename = request.data['new_permission_name']
                if(expanded_permission.permission_mark.id != request.data['new_permission_mark']):
                    expanded_permission.permission_mark = PermissionMark.objects.get(id = request.data['new_permission_mark'])
                if(expanded_permission.group_category.name != request.data['new_category_name']):
                    expanded_permission.group_category = category
                if(accs.path != request.data['path']):
                    accs.path = request.data['path']
                if(accs.component_id != request.data['component_id']):
                    accs.component_id = request.data['component_id']
                if(accs.typeaccession != request.data['accession_type']):
                    accs.typeaccession = request.data['accession_type']
                permission.save()
                expanded_permission.save()
                accs.save()
                return Response(
                    status=status.HTTP_200_OK
                )
            else:
                return Response( 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class RemoveUserPermission(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Удаление права пользователя",
        responses={
            200: "Право удалено пользователю",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
                'permissions_name': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Items(type=openapi.TYPE_STRING), description='Имя права')
            }
        )
    )
    def delete(self, request: Request):     
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
                break
        if(access or request.user.is_superuser):
            user = User.objects.get(username = request.data['username'])
            if(request.user.is_superuser):
                for permission_name in request.data['permissions_name']:
                    permission = Permission.objects.get(name = permission_name)
                    user.user_permissions.remove(permission)
            else:
                catlist =[]
                for exp in exps:
                    if(exp.permission_mark.id==9):
                        catlist.append(exp.group_category)
                for permission_name in request.data['permissions_name']:
                    permission = Permission.objects.get(name = permission_name)
                    exp_permission = ExpandedPermission.objects.get(permission=permission)
                    cat_acc = False
                    for cat in catlist:
                        if(cat == exp_permission.group_category):
                            cat_acc = True
                    if(cat_acc):
                        user.user_permissions.remove(permission)
                    else:
                        return Response(status=status.HTTP_400_BAD_REQUEST)
            user.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
class GetPermissionsByCategory(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав по категории",
        responses={
            200: "Права по категории получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, description="Категория", type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request: Request):
        access = False
        category_name = request.query_params['category']
        category = GroupCategory.objects.get(name = category_name)
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9 and exp.group_category==category:
                access = True
                break
        if(access or request.user.is_superuser):
            expanded_permissions = ExpandedPermission.objects.filter(group_category = category)
            permissions_list = []
            for permission in expanded_permissions:
                perm = permission.permission
                permissions_list.append(perm.name)
            result = {'permissions':permissions_list}
            return Response(
                result,
                status=status.HTTP_200_OK
            )
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
#Проверка на доступ к компонентам и странице
class CheckAccesstoPage(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав пользователя.",
        responses={
            200: "Права пользователя получены",
            401: "Пользователь не авторизован"
        },
        manual_parameters=[
        openapi.Parameter('path', openapi.IN_QUERY, description="Path of page", type=openapi.TYPE_STRING),
    ],
    )
    def get(self, request: Request):
        result = {'access':False}
        if(request.user.is_superuser):
            result['access'] = True
        else:
            id = request.user.id
            groups = Group.objects.filter(user = id)
            permisson_list = []
            for group in groups:
                perms = Permission.objects.filter(group = group)
                for perm in perms:
                    permisson_list.append(perm)
            perms = Permission.objects.filter(user = id)
            for perm in perms:
                permisson_list.append(perm)
            for perm in permisson_list:
                expanded_permission = ExpandedPermission.objects.get(permission_id = perm.id)
                accession = Accession.objects.get(permission = expanded_permission)
                if(accession.typeaccession == 'PageAccession' and accession.path == request.query_params.get('path') and expanded_permission.permission_mark.id == 8):
                    result['access'] = True
                    break
        return Response(
            result,
            status=status.HTTP_200_OK
        )
class CheckAccessToComponent(BaseAPIView):

    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав доступа к компоненту",
        responses={
            200: "Права доступа к компоненту получены",
            401: "Пользователь не авторизован"
        },
        manual_parameters=[
        openapi.Parameter('path', openapi.IN_QUERY, description="Path of page", type=openapi.TYPE_STRING),
        openapi.Parameter('component_id', openapi.IN_QUERY, description="Component id", type=openapi.TYPE_INTEGER),
    ],
    )
    def get(self, request: Request):
        result = {'read':False,'write':False,'execute':False}
        if(request.user.is_superuser):
            result = {'read':True,'write':True,'execute':True}
        else:
            id = request.user.id
            groups = Group.objects.filter(user = id)
            permisson_list = []
            for group in groups:
                perms = Permission.objects.filter(group = group)
                for perm in perms:
                    permisson_list.append(perm)
            perms = Permission.objects.filter(user = id)
            for perm in perms:
                permisson_list.append(perm)
            for perm in permisson_list:
                expanded_permission = ExpandedPermission.objects.get(permission = perm)
                accession = Accession.objects.get(permission = expanded_permission)
                if(accession.typeaccession == 'ComponentAccession' and accession.component_id == request.query_params.get('component_id')):
                    markid = expanded_permission.permission_mark.id
                    if(markid-4>=0):
                        result['read'] = True
                        markid -=4
                    if(markid-2>=0):
                        result['write'] = True
                        markid -=2
                    if(markid%2!=0):
                        result['execute'] = True
                        break
        return Response(
            result,
            status=status.HTTP_200_OK
        )
class CheckAccessToAdminPanel(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав доступа к панели администратора",
        responses={
            200: "Права доступа к панели администратора получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
    )
    def get(self, request: Request):
        result = {'access':False}
        perms =[]
        if(request.user.is_superuser):
            result['access'] = True
        else:
            user = request.user
            groups = user.groups.all()
            for group in groups:
                permissions = group.permissions.all()
                for permission in permissions:
                    expanded_permission = ExpandedPermission.objects.get(permission = permission)
                    if(expanded_permission.permission_mark.id == 9):
                        result['access'] = True
                        break
            if(result['access'] == False):
                permissions = user.user_permissions.all()
                for permission in permissions:
                    expanded_permission = ExpandedPermission.objects.get(permission = permission)
                    if(expanded_permission.permission_mark.id == 9):
                        result['access'] = True
                        break
        return Response(
            result,
            status=status.HTTP_200_OK
        )
#Работа с пользователями
class GetUserGroupsAndPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение групп и прав пользователя",
        responses={
            200: "Группы и права пользователя получены",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
    )
    def get(self, request: Request):
        access = False
        ugplist = []
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
        if(access or request.user.is_superuser):
            if(request.user.is_superuser):
                users = User.objects.all()
                for user in users:
                    groups = user.groups.all()
                    groups_user = []
                    if(len(groups) > 0):
                        for group in groups:
                            groups_user.append(group.name)
                    perms = user.user_permissions.all()
                    user_perms = []
                    if(len(perms) > 0):
                        for perm in perms:
                            user_perms.append(perm.name)
                    tmpdict = {'user': user.username, "groups":groups_user,"permissions":user_perms}
                    ugplist.append(tmpdict)
                result = {'users':ugplist}
            else:
                catlist =[]
                for exp in exps:
                    if(exp.permission_mark.id==9):
                        catlist.append(exp.group_category)
                users = User.objects.all()
                for user in users:
                    groups = user.groups.all()
                    groups_user = []
                    if(len(groups) > 0):
                        for group in groups:
                            exp_group = ExpandedGroup.objects.get(group=group)
                            for cat in catlist:
                                if(exp_group.group_category==cat):
                                    groups_user.append(group.name)
                    perms = user.user_permissions.all()
                    user_perms = []
                    if(len(perms) > 0):
                        for perm in perms:
                            exp_perm = ExpandedPermission.objects.get(perm)
                            for cat in catlist:
                                if(exp_perm.group_category == cat):
                                    user_perms.append(perm.name)
                    tmpdict = {'user': user.username, "groups":groups_user,"permissions":user_perms}
                    ugplist.append(tmpdict)
                result = {'users':ugplist}
            return Response(
                result,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN
            )
class AddUserGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Добавление пользователя в группу",
        responses={
            200: "Пользователь добавлен в группу",
            401: "Пользователь не авторизован",
            403: "Нет доступа"  
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
                'groups_name': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Items(type=openapi.TYPE_STRING), description='Имя группы')
            }
        )
    )
    def post(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
                break
        if(access or request.user.is_superuser):
            if(request.user.is_superuser):
                user = User.objects.get(username = request.data['username'])
                for group_name in request.data['groups_name']:
                    group = Group.objects.get(name = group_name)
                    user.groups.add(group)
                user.save()
            else:
                catlist =[]
                for exp in exps:
                    if(exp.permission_mark.id==9):
                        catlist.append(exp.group_category)
                user = User.objects.get(username = request.data['username'])
                for group_name in request.data['groups_name']:
                    group = Group.objects.get(name = group_name)
                    exp_group = ExpandedGroup.objects.get(group=group)
                    cat_checked = False
                    for cat in catlist:
                        if(cat == exp_group.group_category):
                            cat_checked = True
                    if(cat_checked):
                        user.groups.add(group)
                    else:
                        return Response(status=status.HTTP_403_FORBIDDEN)
                user.save()
        return Response(status=status.HTTP_200_OK)  
class RemoveUserGroup(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Удаление пользователя из группы",
        responses={
            200: "Пользователь удален из группы",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
                'groups_name': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Items(type=openapi.TYPE_STRING), description='Имя группы')
            }
        )
    )
    def delete(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
                break
        if(access or request.user.is_superuser):
            if(request.user.is_superuser):
                user = User.objects.get(username = request.data['username'])
                for group_name in request.data['groups_name']:
                    group = Group.objects.get(name = group_name)
                    user.groups.remove(group)
                user.save()
            else :
                catlist =[]
                for exp in exps:
                    if(exp.permission_mark.id==9):
                        catlist.append(exp.group_category)
                user = User.objects.get(username = request.data['username'])
                for group_name in request.data['groups_name']:
                    group = Group.objects.get(name = group_name)
                    exp_group = ExpandedGroup.objects.get(group=group)
                    cat_checked = False
                    for cat in catlist:
                        if(cat == exp_group.group_category):
                            cat_checked = True
                    if(cat_checked):
                        user.groups.remove(group)
                    else:
                        return Response(status=status.HTTP_403_FORBIDDEN)
                user.save()
        return Response(status=status.HTTP_200_OK)   
class AddUserPermission(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Добавление права пользователю",
        responses={
            200: "Право добавлено пользователю",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
                'permissions_name': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Items(type=openapi.TYPE_STRING), description='Имя права')
            }
        )
    )
    def post(self, request: Request):
        access = False
        exps = GetUserExpandedPermissions(request.user)
        for exp in exps:
            if exp.permission_mark.id == 9:
                access = True
                break
        if(access or request.user.is_superuser):
            user = User.objects.get(username = request.data['username'])
            if(request.user.is_superuser):
                for permission_name in request.data['permissions_name']:
                    permission = Permission.objects.get(name = permission_name)
                    user.user_permissions.add(permission)
                user.save()
            else:
                catlist =[]
                for exp in exps:
                    if(exp.permission_mark.id==9):
                        catlist.append(exp.group_category)
                for permission_name in request.data['permissions_name']:
                    permission = Permission.objects.get(name = permission_name)
                    exp_permission = ExpandedPermission.objects.get(permission=permission)
                    cat_acc = False
                    for cat in catlist:
                        if(cat == exp_permission.group_category):
                            cat_acc = True
                    if(cat_acc):
                        user.user_permissions.add(permission)
                    else:
                        return Response(status=status.HTTP_400_BAD_REQUEST)
                user.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
#Работа с текущим пользователем    
class GetUserName(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение имен пользователей",
        responses={
            200: "Имена пользователей получены",
            401: "Пользователь не авторизован",
        },
    )
    def get(self, request: Request):
        user = request.user
        return Response(
            user.username,
            status=status.HTTP_200_OK
        )
class GetUserGroups(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение групп пользователя",
        responses={
            200: "Группы пользователя",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
    )
    def get(self, request: Request):
        user = request.user
        groups = Group.objects.all()
        groups_list = []
        for group in groups:
            groups_list.append(group.name)
        result = {'groups':groups_list}
        return Response(
            result,
            status=status.HTTP_200_OK
        )
class GetUserPermissions(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение прав пользователя",
        responses={
            200: "Права пользователя",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
    )
    def get(self, request: Request):
        user = request.user
        permissions = Permission.objects.all()
        permissions_list = []
        for permission in permissions:
            permissions_list.append(permission.name)
        result = {'permissions':permissions_list}
        return Response(
            result,
            status=status.HTTP_200_OK
        )