from django.urls import path


from src.external.crm.tasks.views import SectionTaskView,SectionCreateView,TaskCreateView


urlpatterns = [
    path('section-tasks/', SectionTaskView.as_view(), name='section-tasks'),
    path('section-new/', SectionCreateView.as_view(), name='section_add'),
    path('task-new/', TaskCreateView.as_view(), name='task_add'),
    
]

