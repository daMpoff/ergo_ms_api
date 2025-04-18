from django.db import models
from django.contrib.auth import get_user_model
from ..bi_datasets.models import Dataset

class Chart(models.Model):
    CHART_TYPES = [
    ('line', 'Линейная диаграмма'),
    ('area', 'Диаграмма с областями'),
    ('area_stacked', 'Нормированная диаграмма с областями'),
    ('bar', 'Столбчатая диаграмма'),
    ('bar_stacked', 'Нормированная столбчатая диаграмма'),
    ('line_bar', 'Линейчатая диаграмма'),
    ('line_bar_stacked', 'Нормированная линейчатая диаграмма'),
    ('scatter', 'Точечная диаграмма'),
    ('pie', 'Круговая диаграмма'),
    ('donut', 'Кольцевая диаграмма'),
    ('indicator', 'Индикатор'),
    ('tree', 'Древовидная диаграмма'),
    ('table', 'Таблица'),
    ('pivot', 'Сводная таблица'),
    ('map', 'Карта'),
    ('combo', 'Комбинированная диаграмма'),
]

    name = models.CharField(max_length=255)
    chart_type = models.CharField(max_length=32, choices=CHART_TYPES)
    config = models.JSONField(default=dict)  # Вся визуализация хранится тут
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='charts')
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='charts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name