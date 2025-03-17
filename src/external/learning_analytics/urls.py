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
    path('technologies_send/', TechnologySendView.as_view(), name='technologies_send'),
    path('technologies_put/<int:pk>/', TechnologyPutView.as_view(), name='technologies_put'),
    path('technologies_delete/<int:pk>/', TechnologyDeleteView.as_view(), name='technologies_delete'),
    path('competentions/', CompetentionGetView.as_view(), name='competentions'),
    path('competentions_send/', CompetentionSendView.as_view(), name='competentions_send'),
    path('competentions_put/<int:pk>/', CompetentionPutView.as_view(), name='competentions_put'),
    path('competentions_delete_/<int:pk>/', CompetentionDeleteView.as_view(), name='competentions_delete_'),
    path('employers/', EmployerGetView.as_view(), name='employers'),
    path('employers_send/', EmployerSendView.as_view(), name='employers_send'),
    path('employers_put/<int:pk>/', EmployerPutView.as_view(), name='employers_put'),
    path('employers_delete/<int:pk>/', EmployerDeleteView.as_view(), name='employers_delete'),
]