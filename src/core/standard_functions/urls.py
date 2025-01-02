from django.urls import (
    path
)

from src.core.standard_functions.views import CheckAPIView, ExecuteScriptView

urlpatterns = [
    path('check_database_connection/', CheckAPIView.as_view(), name='check-database-connection'),
    path('execute/', ExecuteScriptView.as_view(), name='execute-script'),
]