from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, TaskViewSet, TaskCommentViewSet, TimeLogViewSet, UserViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'task-comments', TaskCommentViewSet)
router.register(r'time-logs', TimeLogViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('strategic-projects/', include('src.external.crm.strategic_projects.urls')),
    path('api/', include(router.urls)),
]