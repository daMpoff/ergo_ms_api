from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, TaskViewSet, TaskCommentViewSet, TimeLogViewSet, UserViewSet,
    ProjectStatusViewSet, ProjectPriorityViewSet, TaskStatusViewSet, TaskPriorityViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'task-comments', TaskCommentViewSet)
router.register(r'time-logs', TimeLogViewSet)
router.register(r'users', UserViewSet)

# Статусы и приоритеты
router.register(r'project-statuses', ProjectStatusViewSet)
router.register(r'project-priorities', ProjectPriorityViewSet)
router.register(r'task-statuses', TaskStatusViewSet)
router.register(r'task-priorities', TaskPriorityViewSet)

urlpatterns = [
    path('', include(router.urls)),
]