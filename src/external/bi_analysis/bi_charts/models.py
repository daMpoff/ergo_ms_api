from django.db import models
from django.conf import settings

class Chart(models.Model):
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, default='')
    dataset = models.ForeignKey('bi_analysis_bi_datasets.Dataset', on_delete=models.CASCADE)
    chart_type = models.CharField(max_length=32)
    engine = models.CharField(max_length=32, default='apex')
    params = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charts'
    )