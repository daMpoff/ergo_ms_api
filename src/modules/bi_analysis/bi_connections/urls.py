from django.urls import path

from src.modules.bi_analysis.bi_connections.views import ConnectionListCreateView, ConnectionDetailView, CheckConnectionView, ConnectionTablesView

urlpatterns = [
    path('', ConnectionListCreateView.as_view(), name='connection-list-create'),
    path('<int:pk>/', ConnectionDetailView.as_view(), name='connection-detail'),
    path("check-connection/", CheckConnectionView.as_view(), name="check-connection"),
    path('<int:connection_id>/tables/', ConnectionTablesView.as_view(), name='connection-tables'),
]