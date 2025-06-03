from django.urls import path
from src.external.crm.projects.views import ProjectCreateView, UserAllProjectsView,PersonalProjectsView,InvitedProjectsView,DeletePersonalProjectView,ProjectTasksCountView,LeaveProjectView

urlpatterns = [
    path('project-new-add/', ProjectCreateView.as_view(), name='project-new'),
    path('project-all/', UserAllProjectsView.as_view(), name='project-all'),
    path('project-personal/', PersonalProjectsView.as_view(), name='project-personal'),
    path('project-invited/', InvitedProjectsView.as_view(), name='project-invited'),
    path('delete-project/<int:project_id>/', DeletePersonalProjectView.as_view(), name='delete_project'),
    path('leave-project/<int:user_id>/<int:project_id>/', LeaveProjectView.as_view(), name='leave_project'),
    path('tasks-count/', ProjectTasksCountView.as_view(), name='project-tasks-count'),
]