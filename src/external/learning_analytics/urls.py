from django.urls import path
from src.external.learning_analytics.views import (
    TechnologyGetView,
    SendTechnologyView
)

urlpatterns = [
    path('technologies/', TechnologyGetView.as_view(), name='technologies'),
    path('send_technologies/', SendTechnologyView.as_view(), name='send_technologies'),
]