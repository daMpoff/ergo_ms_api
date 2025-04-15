from django.urls import (
    path, include
)
from src.core.cms.views import (GetUserPermissions, GetUserGroup, GetUserGroupPermissions, GetGroupPermissions, AddGroup, AddPermission,
DeleteGroup, DeletePermission, UpdateGroup, UpdatePermissionCodeName, UpdatePermissionName)
urlpatterns = [
     path('get-user-permissions/', GetUserPermissions.as_view(), name='get user permissinos'),
     path('get-user-group/', GetUserGroup.as_view(), name='get user group'),
     path('get-user-group-permissions/', GetUserGroupPermissions.as_view(), name='get user permissinos by group'),
     path('get_group_permissions/', GetGroupPermissions.as_view(), name='group permissions'),
     path('add_group/', AddGroup.as_view(), name='add group'),
     path('add_permission', AddPermission.as_view(), name='add permission'),
     path('delete_group/', DeleteGroup.as_view(), name='delete group'),
     path('delete_permission/', DeletePermission.as_view(), name='delete permission'),
     path('update_group/', UpdateGroup.as_view(), name='update group'),
     path('update_permission_name/', UpdatePermissionName.as_view(), name='update permission name'),
     path('update_permission_codename/', UpdatePermissionCodeName.as_view(), name='update permission codename'),
]
