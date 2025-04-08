from django.db import models

# Создавайте свои модели здесь

class GenericStorage(models.Model): # Модель классификации данных
    STORAGE_TYPE_CHOICES = [
        ('structured', 'Структурированные'),
        ('semi', 'Полуструктурированные (JSON, XML, логи)'),
        ('unstructured', 'Неструктурированные (файлы, изображения, видео)'),
    ]

    storage_type = models.CharField(
        max_length=20,
        choices=STORAGE_TYPE_CHOICES
    )

    name = models.CharField(max_length=255)  # имя или ID источника
    description = models.TextField(blank=True, null=True)

    # Поля для разных типов
    json_data = models.JSONField(blank=True, null=True)       # semi-structured
    file = models.FileField(upload_to="storage/", blank=True, null=True)  # unstructured
    table_ref = models.CharField(max_length=255, blank=True, null=True)   # structured (имя таблицы/источника)

    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.storage_type})"