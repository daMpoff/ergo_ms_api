from django.db import models

# Создавайте свои модели здесь
class StagingGenericData(models.Model):
    source = models.CharField(max_length=255)
    ingest_timestamp = models.DateTimeField(auto_now_add=True)
    raw_data = models.JSONField()
    processed = models.BooleanField(default=False)
    additional_info = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.source} (ID: {self.id})"