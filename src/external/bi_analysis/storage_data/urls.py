from django.urls import path
from .views import GenericStorageView, FileUploadView

urlpatterns = [
    path('', GenericStorageView.as_view(), name='storage-list-create'),
    path('upload/', FileUploadView.as_view(), name='storage-upload'),
]