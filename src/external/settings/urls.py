from django.urls import (
    path, include
)
from .views import FileViewSet
from rest_framework.routers import DefaultRouter
from .views import *
router = DefaultRouter()
router.register(r'general-settings', GeneralSettingsViewSet)
router.register(r'appearance-settings', AppearanceSettingsViewSet)
router.register(r'security-settings', SecuritySettingsViewSet)
router.register(r'media-settings', MediaSettingsViewSet)
router.register(r'permalink-settings', PermalinkSettingsViewSet)
router.register(r'email-settings', EmailSettingsViewSet)
router.register(r'file', FileViewSet)

urlpatterns = [
     path('', include(router.urls)),
]
