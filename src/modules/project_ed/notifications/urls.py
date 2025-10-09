from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectNotificationViewSet

router = DefaultRouter()
router.register(r'', ProjectNotificationViewSet, basename='project-ed-notifications')

urlpatterns = [
    path('', include(router.urls)),
]