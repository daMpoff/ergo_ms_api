from django.urls import path
from src.external.expsys_module.views import PostCompetenciesandVacations
from src.external.expsys_module.views import  TeacherSubjectsView,SubjectCreateView,SubjectIndicatorsCompetenciesView,CompetenciesView

urlpatterns = [
     path('post-competencies-vacations', PostCompetenciesandVacations.as_view(), name='post competencies and vacations'),
     path('subjects-all/', TeacherSubjectsView.as_view(), name='subjects-all'),
     path('subject-create/', SubjectCreateView.as_view(), name='subject-create'),
     path('subjectsindicators/', SubjectIndicatorsCompetenciesView.as_view(), name='subjectsindicators'),
      path('allcompetencies/', CompetenciesView.as_view(), name='allcompetencies'),
]