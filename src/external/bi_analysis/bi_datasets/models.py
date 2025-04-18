from django.db import models
from django.contrib.auth import get_user_model

class Dataset(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    owner = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='datasets'
    )

    # Источник — один из двух:
    file_source = models.ForeignKey(
        'bi_analysis_bi_datasets.FileUpload',  # <== уточнение: app_name.ModelName
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    connection = models.ForeignKey(
        'bi_analysis_bi_connections.Connection',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    table_ref = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name
    
class FileUpload(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='uploaded_files')

    # можно добавить метаинформацию
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)  # 'csv', 'xlsx', ...

    def __str__(self):
        return self.name
