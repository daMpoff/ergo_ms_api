from django.db import models
from django.contrib.auth import get_user_model
from src.external.bi_analysis.bi_connections.models import Connection

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

    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

class Dataset(models.Model):
    is_temporary = models.BooleanField(default=False)
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

    def __str__(self):
        return self.name


class DataSetTable(models.Model):
    dataset    = models.ForeignKey(
        Dataset,
        related_name="tables",
        on_delete=models.CASCADE
    )
    connection = models.ForeignKey(
        Connection,
        on_delete=models.CASCADE,
        related_name='dataset_tables'
    )
    table_name = models.CharField(max_length=200)
    alias      = models.CharField(max_length=100, blank=True)
    joined_on  = JSONField(default=dict)
    order      = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
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
