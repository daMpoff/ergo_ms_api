from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone




class Connections(models.Model):
    name = models.CharField(max_length=255, default='')
    connector_type = models.CharField(max_length=50, default='')
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

class FileUpload(models.Model):
    name = models.CharField(max_length=255, default='')
    file_character = models.CharField(max_length=100, default='')
    uploaded_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    original_file_name = models.CharField(max_length=255, default='')
    file_type = models.CharField(max_length=50, default='')

class Dataset(models.Model):
    name = models.CharField(max_length=255, default='')
    description = models.TextField(default='')
    created_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    connection = models.ForeignKey(Connections, on_delete=models.CASCADE)
    table_ref = models.CharField(max_length=255, default='')
    file_upload = models.ForeignKey(FileUpload, on_delete=models.CASCADE)

class Charts(models.Model):
    name = models.CharField(max_length=255, default='')
    chart_type = models.CharField(max_length=32, default='')
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
