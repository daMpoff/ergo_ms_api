from django.urls import path
from .views import StagingDataView

urlpatterns = [
    path('', StagingDataView.as_view(), name='staging-data'),
]