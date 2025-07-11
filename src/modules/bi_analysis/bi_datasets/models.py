from django.db import models
from django.contrib.auth import get_user_model
from src.modules.bi_analysis.bi_connections.models import Connection

JSONField = models.JSONField

TYPE_CHOICES = [
    ('geopolygon', 'Геополигон'),
    ('geopoint',   'Геоточка'),
    ('date',       'Дата'),
    ('date&time',  'Дата и время'),
    ('float',      'Дробное число'),
    ('bool',       'Логический'),
    ('string',     'Строка'),
    ('integer',    'Целое число'),
]

AGG_CHOICES = [
    ('none', 'Нет'),
    ('count', 'Количество'),
    ('ucount', 'Количество уникальных'),
    ('max',   'Максимум'),
    ('min',   'Минимум'),
    ('avg',   'Среднее'),
    ('sum',   'Сумма'),
]

class FileUpload(models.Model):
    name = models.CharField(max_length=255)
    connection = models.ForeignKey(Connection, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='uploaded_files')
    columns_info = models.JSONField(null=True, blank=True, default=dict)

    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

class Dataset(models.Model):
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    owner       = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='datasets'
    )
    file_source = models.ForeignKey(
        'bi_analysis_bi_datasets.FileUpload',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    connection  = models.ForeignKey(
        Connection,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='datasets'
    )
    table_ref   = models.CharField(max_length=255, blank=True, null=True)

    def fields_for_current_dataset(self):
        return self.fields.all()
    
    def __str__(self):
        return self.name


class DataSetTable(models.Model):
    dataset    = models.ForeignKey(
        Dataset, related_name="tables", on_delete=models.CASCADE
    )
    connection = models.ForeignKey(
        Connection, related_name="dataset_tables", on_delete=models.CASCADE
    )

    table_name = models.CharField(max_length=200)
    alias      = models.CharField(max_length=100, blank=True)

    # ключ и порядок
    joined_on  = models.JSONField(default=dict)      # {type, left, right}
    order      = models.PositiveSmallIntegerField(default=0)

    # ← ОСТАВЛЯЕМ ровно ОДНО поле file_upload
    file_upload  = models.ForeignKey(
        FileUpload, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="dataset_tables"
    )

    # «человеческое» имя и схема колонок
    display_name = models.CharField(max_length=255, blank=True)
    columns_info = models.JSONField(null=True, blank=True)

    # --- новые атрибуты ---
    sheet_name       = models.CharField(max_length=255, blank=True, null=True)
    joined_on_type   = models.CharField(max_length=16,  blank=True, null=True)
    joined_on_left   = models.CharField(max_length=128, blank=True, null=True)
    joined_on_right  = models.CharField(max_length=128, blank=True, null=True)

    # ----------------------

    def save(self, *args, **kwargs):
        """Если таблица привязана к FileUpload — подтянуть имя и columns_info."""
        if self.file_upload_id:
            if not self.display_name:
                self.display_name = self.file_upload.original_filename

            if self.columns_info is None and self.file_upload.columns_info:
                self.columns_info = self.file_upload.columns_info

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.dataset.name} → {self.table_name}"


class DataSetField(models.Model):
    dataset       = models.ForeignKey(
        Dataset,
        related_name="fields",
        on_delete=models.CASCADE
    )
    name          = models.CharField(max_length=200)
    source_table  = models.ForeignKey(
        DataSetTable,
        related_name="fields",
        on_delete=models.CASCADE
    )
    source_column = models.CharField(max_length=200) 
    expression    = models.TextField(blank=True)
    type          = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='string'
    )
    aggregation   = models.CharField(
        max_length=20,
        choices=AGG_CHOICES,
        default='none'
    )
    order         = models.PositiveSmallIntegerField(default=0)
    description   = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.dataset.name}.{self.name}"
