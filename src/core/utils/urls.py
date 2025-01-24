"""
Файл содержащий маршруты (URL-patterns) для Django-приложения.
"""

from django.urls import (
    path
)

from src.core.utils.views import (
    CheckDatabaseConnectionView,
)

urlpatterns = [
    path('check-database-connection/', CheckDatabaseConnectionView.as_view(), name='check-database-connection'),
]