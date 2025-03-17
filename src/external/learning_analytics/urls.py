from django.urls import path

# Импортируем представления данных для определения путей к ним
from src.external.learning_analytics.views import (
    EmployerSendView,
    EmployerGetView,
    EmployerPutView,
    EmployerDeleteView,
    CompetentionSendView,
    CompetentionGetView,
    CompetentionPutView,
    CompetentionDeleteView,
    TechnologySendView,
    TechnologyGetView,
    TechnologyPutView,
    TechnologyDeleteView
)

urlpatterns = [
    path('technologies/', TechnologyGetView.as_view(), name='technologies'),
    path('send_technologies/', TechnologySendView.as_view(), name='send_technologies'),
    path('put_technologies/', TechnologyPutView.as_view(), name='put_technologies'),
    path('delete_technologies/', TechnologyDeleteView.as_view(), name='delete_technologies'),
    path('competentions/', CompetentionGetView.as_view(), name='competentions'),
    path('send_competentions/', CompetentionSendView.as_view(), name='send_competentions'),
    path('put_competentions/', CompetentionPutView.as_view(), name='put_competentions'),
    path('delete_competentions/', CompetentionDeleteView.as_view(), name='delete_competentions'),
    path('employers/', EmployerGetView.as_view(), name='employers'),
    path('send_employers/', EmployerSendView.as_view(), name='send_employers'),
    path('put_employers/', EmployerPutView.as_view(), name='put_employers'),
    path('delete_employers/', EmployerDeleteView.as_view(), name='delete_employers'),
]