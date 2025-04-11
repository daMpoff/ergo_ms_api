from django.urls import path
from src.external.crm.projects.views import ProjectCreateView, UserAllProjectsView

urlpatterns = [
    path('project-new-add/', ProjectCreateView.as_view(), name='project-new'),
    path('project-all/', UserAllProjectsView.as_view(), name='project-all'),


]