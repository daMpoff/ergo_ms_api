from django.urls import path
from src.external.bi_analysis.bi_charts.views import ChartListCreateView, ChartDetailView

urlpatterns = [
    path('', ChartListCreateView.as_view(), name='chart-list-create'),
    path('<int:pk>/', ChartDetailView.as_view(), name='chart-detail'),
]