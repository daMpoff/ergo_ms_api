from django.urls import path
from .views import ConnectionListCreateView, ConnectionDetailView

urlpatterns = [
    path('', ConnectionListCreateView.as_view(), name='connection-list-create'),
    path('<int:pk>/', ConnectionDetailView.as_view(), name='connection-detail'),
]