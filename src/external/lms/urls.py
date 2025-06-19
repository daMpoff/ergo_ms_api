from django.urls import path, include
from src.external.lms.views import AnalyticsViewSet

app_name = 'lms'

urlpatterns = [
    # Analytics endpoints
    path('analytics/student_stats/', AnalyticsViewSet.as_view({'get': 'student_stats'})),
    path('analytics/teacher_stats/', AnalyticsViewSet.as_view({'get': 'teacher_stats'})),
]
