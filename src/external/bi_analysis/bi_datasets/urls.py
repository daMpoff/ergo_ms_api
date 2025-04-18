from django.urls import path
from .views import DatasetListCreateView, DatasetDetailView, FileUploadView, FileUploadListView, FileUploadDetailView

urlpatterns = [
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
    path('<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('upload/<int:pk>/', FileUploadDetailView.as_view(), name='file-upload-detail'),
    path('user-files/', FileUploadListView.as_view(), name='file-upload-list'),
]