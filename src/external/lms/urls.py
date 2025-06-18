from django.urls import path, include
from src.external.lms.views import AnalyticsViewSet

app_name = 'lms'

urlpatterns = [
    # Analytics endpoints
    path('analytics/student_stats/', AnalyticsViewSet.as_view({'get': 'student_stats'})),
    path('analytics/teacher_stats/', AnalyticsViewSet.as_view({'get': 'teacher_stats'})),

    # Include submodules
    path('assignments/', include('src.external.lms.assignments.urls')),
    path('assessment/', include('src.external.lms.assessment.urls')),
    path('courses/', include('src.external.lms.courses.urls')),
    path('users/', include('src.external.lms.users.urls')),
]
