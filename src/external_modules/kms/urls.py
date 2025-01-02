from django.urls import (
    path
)

from src.external_modules.kms.views import FileUploadView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
]