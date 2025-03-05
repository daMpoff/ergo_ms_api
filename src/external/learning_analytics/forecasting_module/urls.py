from django.urls import path
from src.external.learning_analytics.forecasting_module.views import (
    SpecialityGetView,
    SendSpecialityView,
    DisciplineGetView,
    SendDisciplineView
)

urlpatterns = [
    path('specialities/', SpecialityGetView.as_view(), name='specialities'),
    path('send_specialitiy/', SendSpecialityView.as_view(), name='send_speciality'),
    path('disciplines/', DisciplineGetView.as_view(), name='disciplines'),
    path('send_disciplines/', SendDisciplineView.as_view(), name='send_discipline'),
]