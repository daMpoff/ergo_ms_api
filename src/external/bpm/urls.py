from django.urls import (
    path
)

from src.external.bpm.views import TasksView

urlpatterns = [
    path('tasks/', TasksView.as_view(), name='tasks'),
]