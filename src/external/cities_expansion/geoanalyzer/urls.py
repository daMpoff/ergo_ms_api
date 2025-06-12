from django.urls import path

from src.external.cities_expansion.geoanalyzer.views import UploadMaps
from src.external.cities_expansion.geoanalyzer.views import PerformAnalysis
from src.external.cities_expansion.geoanalyzer.views import TaskStatus

urlpatterns = [
    path('upload_maps', UploadMaps.as_view(), name='upload_maps'),
    path('perform_analysis', PerformAnalysis.as_view(), name='perform_analysis'),
    path('task_status', TaskStatus.as_view(), name='task_status'),
]