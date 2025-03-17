from django.urls import path

# Импортируем представления данных для определения путей к ним
from src.external.learning_analytics.views import (
    TechnologyGetView,
    CompetentionGetView,
    EmployerGetView,
    SendTechnologyView,
    SendCompetentionView,
    SendEmployerView,
    EmployerPutView,
    EmployerDeleteView,
    CompetentionPutView,
    CompetentionDeleteView
)

urlpatterns = [
    path('technologies/', TechnologyGetView.as_view(), name='technologies'),
    path('send_technologies/', SendTechnologyView.as_view(), name='send_technologies'),
    path('competentions/', CompetentionGetView.as_view(), name='competentions'),
    path('send_competentions/', SendCompetentionView.as_view(), name='send_competentions'),
    path('employers/', EmployerGetView.as_view(), name='employers'),
    path('send_employers/', SendEmployerView.as_view(), name='send_employers'),
    path('put_employers/', EmployerPutView.as_view(), name='put_employers'),
    path('delete_employers/', EmployerDeleteView.as_view(), name='delete_employers'),
    path('put_competentions/', CompetentionPutView.as_view(), name='put_competentions'),
    path('delete_competentions/', CompetentionDeleteView.as_view(), name='delete_competentions'),
]