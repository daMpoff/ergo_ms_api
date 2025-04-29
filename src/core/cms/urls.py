from django.urls import (
    path, include
)
from .views import FileViewSet
from rest_framework.routers import DefaultRouter
from .views import *
from src.core.cms.views import (GetUserPermissions, GetUserGroup, GetUserGroupPermissions)
router = DefaultRouter()
router.register(r'general-settings', GeneralSettingsViewSet)
router.register(r'appearance-settings', AppearanceSettingsViewSet)
router.register(r'seo-settings', SEOSettingsViewSet)
router.register(r'security-settings', SecuritySettingsViewSet)
router.register(r'media-settings', MediaSettingsViewSet)
router.register(r'permalink-settings', PermalinkSettingsViewSet)
router.register(r'email-settings', EmailSettingsViewSet)
router.register(r'file', FileViewSet)

urlpatterns = [
     path('', include(router.urls)),
     path('get-user-permissions', GetUserPermissions.as_view(), name='get user permissinos'),
     path('get-user-group', GetUserGroup.as_view(), name='get user group'),
     path('get-user-group-permissions', GetUserGroupPermissions.as_view(), name='get user permissinos by group'),
]
