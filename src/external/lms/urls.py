from django.urls import (
    path
)

from src.external.lms.views import CoursesView

urlpatterns = [
    path('courses/', CoursesView.as_view(), name='courses'),
]