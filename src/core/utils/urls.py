"""
Файл содержащий маршруты (URL-patterns) для Django-приложения.
"""

from django.urls import (
    path
)

from src.core.utils.views import (
    CheckAPIView,
)

urlpatterns = [
    path('check-database-connection/', CheckAPIView.as_view(), name='check-database-connection'),
]