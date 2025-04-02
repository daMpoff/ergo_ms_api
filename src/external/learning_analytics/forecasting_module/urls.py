from django.urls import path
from src.external.learning_analytics.forecasting_module.views import (
    SpecialityGetView,
    SpecialitySendView,
    SpecialityPutView,
    SpecialityDeleteView,
    DisciplineGetView,
    DisciplineSendView,
    DisciplinePutView,
    DisciplineDeleteView,
    AcademicCompetenceMatrixGetView,
    AcademicCompetenceMatrixSendView,
    AcademicCompetenceMatrixPutView,
    AcademicCompetenceMatrixDeleteView,
    CompetencyProfileOfVacancyGetView,
    CompetencyProfileOfVacancySendView,
    CompetencyProfileOfVacancyPutView,
    CompetencyProfileOfVacancyDeleteView
)

urlpatterns = [
    path('specialities/', SpecialityGetView.as_view(), name='specialities'),
    path('send_specialitiy/', SpecialitySendView.as_view(), name='send_speciality'),
    path('speciality_put/<int:pk>/', SpecialityPutView.as_view(), name='speciality_put'),
    path('speciality_delete/<int:pk>/', SpecialityDeleteView.as_view(), name='speciality_delete'),
    path('disciplines/', DisciplineGetView.as_view(), name='disciplines'),
    path('disciplines_send/', DisciplineSendView.as_view(), name='send_discipline'),
    path('disciplines_put/<int:pk>/', DisciplinePutView.as_view(), name='discipline_put'),
    path('disciplines_delete/<int:pk>/', DisciplineDeleteView.as_view(), name='discipline_delete'),
    path('academic_competence_matrix/', AcademicCompetenceMatrixGetView.as_view(), name='academic_competence_matrix'),
    path('academic_competence_matrix_send/', AcademicCompetenceMatrixSendView.as_view(), name='send_academic_competence_matrix'),
    path('academic_competence_matrix_put/<int:pk>/', AcademicCompetenceMatrixPutView.as_view(), name='academic_competence_matrix_put'),
    path('academic_competence_matrix_delete/<int:pk>/', AcademicCompetenceMatrixDeleteView.as_view(), name='academic_competence_matrix_delete'),
    path('competency_profiles_of_vacancies/', CompetencyProfileOfVacancyGetView.as_view(), name='competency_profiles_of_vacancies'),
    path('competency_profiles_of_vacancies_send/', CompetencyProfileOfVacancySendView.as_view(), name='send_competency_profiles_of_vacancies'),
    path('competency_profiles_of_vacancies_put/<int:pk>/', CompetencyProfileOfVacancyPutView.as_view(), name='competency_profiles_of_vacancies_put'),
    path('competency_profiles_of_vacancies_delete/<int:pk>/', CompetencyProfileOfVacancyDeleteView.as_view(), name='competency_profiles_of_vacancies_delete'),
]