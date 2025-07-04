from django.db import models
from django.contrib.auth.models import User
import uuid
import os


class PorosityAnalysis(models.Model):
    """Модель для хранения информации об анализе пористости"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='porosity_analyses')
    
    # Основная информация
    title = models.CharField(max_length=200, verbose_name="Название анализа")
    description = models.TextField(blank=True, verbose_name="Описание")
    
    # Параметры анализа
    original_image = models.ImageField(upload_to='porosity_analysis/images/', verbose_name="Исходное изображение")
    scale_value = models.FloatField(verbose_name="Значение шкалы (мкм)", help_text="Значение шкалы в микрометрах")
    
    # Статус обработки
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('error', 'Ошибка'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    error_message = models.TextField(blank=True, verbose_name="Сообщение об ошибке")
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Обработано")
    
    class Meta:
        verbose_name = "Анализ пористости"
        verbose_name_plural = "Анализы пористости"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} ({self.user.username})"
        
    def get_results_directory(self):
        """Возвращает путь к директории с результатами"""
        return f"porosity_analysis/results/{self.id}/"


class PorosityResult(models.Model):
    """Модель для хранения результатов анализа пористости"""
    
    analysis = models.OneToOneField(PorosityAnalysis, on_delete=models.CASCADE, related_name='result')
    
    # Основные метрики пористости
    porosity_percentage = models.FloatField(verbose_name="Пористость (%)")
    relative_pore_area = models.FloatField(verbose_name="Относительная площадь пор (%)")
    number_of_pores = models.IntegerField(verbose_name="Количество пор")
    
    # Статистика размеров пор
    mean_pore_size_microns = models.FloatField(verbose_name="Средний размер поры (мкм²)")
    median_pore_size_microns = models.FloatField(verbose_name="Медианный размер поры (мкм²)")
    mean_pore_diameter_microns = models.FloatField(verbose_name="Средний диаметр поры (мкм)")
    median_pore_diameter_microns = models.FloatField(verbose_name="Медианный диаметр поры (мкм)")
    
    # Информация о масштабе
    pixels_per_micron = models.FloatField(verbose_name="Пикселей на микрометр")
    scale_region_x = models.IntegerField(verbose_name="X координата области шкалы")
    scale_region_y = models.IntegerField(verbose_name="Y координата области шкалы") 
    scale_region_width = models.IntegerField(verbose_name="Ширина области шкалы")
    scale_region_height = models.IntegerField(verbose_name="Высота области шкалы")
    
    # Статистика исключенных областей
    total_pixels = models.IntegerField(verbose_name="Общее количество пикселей")
    scale_excluded_pixels = models.IntegerField(verbose_name="Исключено пикселей шкалы")
    lines_excluded_pixels = models.IntegerField(verbose_name="Исключено пикселей линий")
    anomalies_excluded_pixels = models.IntegerField(verbose_name="Исключено аномальных пикселей")
    total_excluded_pixels = models.IntegerField(verbose_name="Общее количество исключенных пикселей")
    
    # Расширенные метрики (JSON для гибкости)
    extended_metrics = models.JSONField(default=dict, blank=True, verbose_name="Расширенные метрики")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    
    class Meta:
        verbose_name = "Результат анализа пористости"
        verbose_name_plural = "Результаты анализов пористости"
        
    def __str__(self):
        return f"Результат для {self.analysis.title}"


class AnalysisFile(models.Model):
    """Модель для хранения файлов результатов анализа"""
    
    analysis = models.ForeignKey(PorosityAnalysis, on_delete=models.CASCADE, related_name='files')
    
    FILE_TYPE_CHOICES = [
        ('scale_bar', 'Изображение с шкалой'),
        ('scale_region', 'Область шкалы'),
        ('contrast_stages', 'Этапы обработки контраста'),
        ('excluded_areas', 'Исключенные области'),
        ('texture_clusters', 'Текстурный анализ'),
        ('mask_result', 'Бинарная маска и результат'),
        ('overlay', 'Наложение результатов'),
        ('pore_size_distribution', 'Распределение размеров пор'),
        ('interpore_distances', 'Межпоровые расстояния'),
        ('pore_orientation_rose', 'Роза направлений'),
        ('pore_orientation_histogram', 'Гистограмма ориентации'),
        ('pore_shapes_analysis', 'Анализ форм пор'),
        ('circularity_distribution', 'Распределение кругового фактора'),
        ('ellipticity_vs_area', 'Эллиптичность vs площадь'),
    ]
    
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES, verbose_name="Тип файла")
    file = models.FileField(upload_to='porosity_analysis/results/', verbose_name="Файл")
    filename = models.CharField(max_length=255, verbose_name="Имя файла")
    description = models.CharField(max_length=500, blank=True, verbose_name="Описание")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    
    class Meta:
        verbose_name = "Файл результата анализа"
        verbose_name_plural = "Файлы результатов анализа"
        unique_together = ['analysis', 'file_type']
        
    def __str__(self):
        return f"{self.get_file_type_display()} - {self.analysis.title}"