from django.urls import path
from src.external.learning_analytics.forecasting_module.views import (
    SpecialityGetView,
    SendSpecialityView
)

urlpatterns = [
    path('specialities/', SpecialityGetView.as_view(), name='specialities'),
    path('send_specialitiy/', SendSpecialityView.as_view(), name='send_speciality'),
]