from django.urls import path, include
from src.external.bi_analysis.bi_datasets.views import DataSetFieldViewSet
from src.external.bi_analysis.bi_datasets.views import (
    DatasetListCreateView, DatasetDetailView, DatasetPreviewView,
    FileUploadView, FileUploadDetailView,
    FinalizeUploadView, XlsxSheetListView,
    XlsxTempPreviewView, FileUploadByConnectionView, DataSetFieldViewSet,
    RenameDatasetColumnsView
)
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'fields', DataSetFieldViewSet, basename='dataset-fields')

urlpatterns = [
    path('', include(router.urls)),
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
    path('<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('<int:pk>/preview/', DatasetPreviewView.as_view(), name='dataset-preview'),
    path('<int:pk>/rename_columns/', RenameDatasetColumnsView.as_view()),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('upload/<int:pk>/', FileUploadDetailView.as_view(), name='file-upload-detail'),
    path('upload/finalize/', FinalizeUploadView.as_view(), name='finalize-upload'),
    path('xlsx/sheets/', XlsxSheetListView.as_view(), name='xlsx-sheet-list'),
    path('xlsx/preview/', XlsxTempPreviewView.as_view(), name='xlsx-preview'),
    path('connection/<int:connection_id>/files/', FileUploadByConnectionView.as_view(), name='fileupload-by-connection'),
]