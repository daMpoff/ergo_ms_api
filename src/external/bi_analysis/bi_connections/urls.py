from django.urls import path
from .views import ConnectionListCreateView, ConnectionDetailView, CheckConnectionView

urlpatterns = [
    path('', ConnectionListCreateView.as_view(), name='connection-list-create'),
    path('<int:pk>/', ConnectionDetailView.as_view(), name='connection-detail'),
    path("check-connection/", CheckConnectionView.as_view(), name="check-connection"),
]