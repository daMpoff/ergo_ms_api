from django.urls import path
from src.external.crm.projects.views import ProjectCreateView, UserAllProjectsView,PersonalProjectsView,InvitedProjectsView

urlpatterns = [
    path('project-new-add/', ProjectCreateView.as_view(), name='project-new'),
    path('project-all/', UserAllProjectsView.as_view(), name='project-all'),
    path('project-personal/', PersonalProjectsView.as_view(), name='project-personal'),
    path('project-invited/', InvitedProjectsView.as_view(), name='project-invited'),




]