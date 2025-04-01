from django.urls import (
    path, include
)
from src.core.cms.views import (GetUserPermissions, GetUserGroup, GetUserGroupPermissions)
urlpatterns = [
     path('get-user-permissions', GetUserPermissions.as_view(), name='get user permissinos'),
     path('get-user-group', GetUserGroup.as_view(), name='get user group'),
     path('get-user-group-permissions', GetUserGroupPermissions.as_view(), name='get user permissinos by group'),
]
