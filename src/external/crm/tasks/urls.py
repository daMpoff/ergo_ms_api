from django.urls import path


from src.external.crm.tasks.views import SectionTaskView,SectionCreateView,TaskCreateView,DeleteTaskView,SubtaskCreateView


urlpatterns = [
    path('section-tasks/', SectionTaskView.as_view(), name='section-tasks'),
    path('section-new/', SectionCreateView.as_view(), name='section_add'),
    path('task-new/', TaskCreateView.as_view(), name='task_add'),
    path('delete-task/<int:task_id>/', DeleteTaskView.as_view(), name='delete_task'),
    path('subtask-new/<int:parenttask_id>', SubtaskCreateView.as_view(), name='subtask-new'),
]

