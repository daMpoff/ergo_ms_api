from django.urls import path
from .views import ProjectCreateView

app_name = 'project_ed_projects'

urlpatterns = [
    path('projects/create/', ProjectCreateView.as_view(), name='project-create'),
]