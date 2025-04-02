from django.urls import path
from src.external.expsys_module.views import PostCompetenciesandVacations
urlpatterns = [
     path('post-competencies-vacations', PostCompetenciesandVacations.as_view(), name='post competencies and vacations'),
]