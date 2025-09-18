from django.urls import path, include
from rest_framework.routers import DefaultRouter

from src.modules.project_ed.views import ProjectViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project-projects')

urlpatterns = [
    path('', include(router.urls)),
]