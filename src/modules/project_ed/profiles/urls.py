from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserProfileViewSet,
    UserProfileSettingsViewSet
)

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='user-profiles')
router.register(r'settings', UserProfileSettingsViewSet, basename='profile-settings')

urlpatterns = [
    path('', include(router.urls)),
]