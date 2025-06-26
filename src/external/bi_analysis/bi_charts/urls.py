from django.urls import path
from .views import ChartListCreateView, ChartDetailView, ChartRowsAPIView
from . import views

urlpatterns = [
    path('', ChartListCreateView.as_view(), name='chart-list-create'),
    path('<int:pk>/', ChartDetailView.as_view(), name='chart-detail'),
    path('<int:pk>/columns/', views.dataset_columns, name='bi_charts-dataset-columns'),
    path('<int:pk>/rows/', ChartRowsAPIView.as_view()),
]