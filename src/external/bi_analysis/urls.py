from django.urls import path, include

from .views import RunReportAPIView

urlpatterns = [
    path('run-report/', RunReportAPIView.as_view(), name='run-report'),
    path('storage_data/', include('src.external.bi_analysis.storage_data.urls')),
]