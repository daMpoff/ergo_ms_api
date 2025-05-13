from django.urls import path
from src.external.expsys_module.views import PostCompetenciesandVacations
from src.external.expsys_module.views import  TeacherSubjectsView,SubjectCreateView

urlpatterns = [
     path('post-competencies-vacations', PostCompetenciesandVacations.as_view(), name='post competencies and vacations'),
     path('subjects-all/', TeacherSubjectsView.as_view(), name='subjects-all'),
     path('subject-create/', SubjectCreateView.as_view(), name='subject-create'),

]