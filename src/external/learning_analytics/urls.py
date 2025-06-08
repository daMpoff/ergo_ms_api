from django.urls import path
from src.external.learning_analytics.views import EmployerView, DatabaseTablesView, ClearTablesView, LoadSampleEmployerData

urlpatterns = [
    path('employers/', EmployerView.as_view({'get': 'list', 'post': 'create'}), name='employers'),
    path('employers/<int:pk>/', EmployerView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='employer-detail'),
    path('tables/', DatabaseTablesView.as_view(), name='database-tables'),
    path('tables/clear/', ClearTablesView.as_view(), name='clear-tables'),
    path('employers/loadsampledata/', LoadSampleEmployerData.as_view(), name='load-sample-employers'),
]