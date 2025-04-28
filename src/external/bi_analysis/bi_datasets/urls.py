from django.urls import path
from .views import DatasetListCreateView, DatasetDetailView, FileUploadView, FileUploadDetailView, FinalizeUploadView, XlsxSheetListView, XlsxTempPreviewView, FileUploadByConnectionView

urlpatterns = [
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
    path('<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('upload/<int:pk>/', FileUploadDetailView.as_view(), name='file-upload-detail'),
    path('upload/finalize/', FinalizeUploadView.as_view(), name='finalize-upload'),
    path('xlsx/sheets/', XlsxSheetListView.as_view(), name='xlsx-sheet-list'),
    path('xlsx/preview/', XlsxTempPreviewView.as_view(), name='xlsx-preview'),
    path('connection/<int:connection_id>/files/', FileUploadByConnectionView.as_view(), name='fileupload-by-connection'),
]