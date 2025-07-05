import os
from django.db import models
from django.utils import timezone


class PorosityAnalysis(models.Model):
    """Модель для хранения результатов анализа пористости"""
    
    # Основная информация
    name = models.CharField(max_length=255, verbose_name="Название анализа")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    
    # Пути к файлам
    original_image_uuid = models.CharField(max_length=36, unique=True, verbose_name="UUID исходного изображения")
    results_uuid = models.CharField(max_length=36, unique=True, verbose_name="UUID результатов")
    
    # Параметры анализа
    scale_value = models.FloatField(verbose_name="Значение шкалы (мкм)")
    pixels_per_micron = models.FloatField(null=True, blank=True, verbose_name="Пикселей на микрометр")
    
    # Основные результаты
    porosity_percentage = models.FloatField(null=True, blank=True, verbose_name="Процент пористости")
    number_of_pores = models.IntegerField(null=True, blank=True, verbose_name="Количество пор")
    average_pore_size = models.FloatField(null=True, blank=True, verbose_name="Средний размер пор (мкм)")
    max_pore_size = models.FloatField(null=True, blank=True, verbose_name="Максимальный размер пор (мкм)")
    min_pore_size = models.FloatField(null=True, blank=True, verbose_name="Минимальный размер пор (мкм)")
    
    # Дополнительные метрики
    pore_density = models.FloatField(null=True, blank=True, verbose_name="Плотность пор (пор/мкм²)")
    average_interpore_distance = models.FloatField(null=True, blank=True, verbose_name="Среднее межпоровое расстояние (мкм)")
    
    # Статус анализа
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    error_message = models.TextField(blank=True, verbose_name="Сообщение об ошибке")
    
    class Meta:
        db_table = 'porosity_analysis'
        verbose_name = "Анализ пористости"
        verbose_name_plural = "Анализы пористости"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    @property
    def results_directory(self):
        """Возвращает путь к директории результатов на основе UUID"""
        from django.conf import settings
        return os.path.join(
            settings.MEDIA_ROOT,
            'porosity_analysis',
            'results',
            self.results_uuid
        )
    
    @property
    def original_image_path(self):
        """Возвращает путь к исходному изображению на основе UUID"""
        from django.conf import settings
        return os.path.join(
            settings.MEDIA_ROOT,
            'porosity_analysis',
            'initial_photo',
            f"{self.original_image_uuid}.png"
        )