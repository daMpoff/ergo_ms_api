from django.db import models
from django.contrib.auth.models import User
import uuid


class PorosityAnalysis(models.Model):
    """Модель для хранения результатов анализа пористости"""
    
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='porosity_analyses')
    name = models.CharField(max_length=255, verbose_name='Название анализа')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scale_value = models.FloatField(verbose_name='Значение шкалы (мкм)', default=100.0)
    
    # Основные результаты
    porosity_percentage = models.FloatField(null=True, blank=True, verbose_name='Пористость (%)')
    number_of_pores = models.IntegerField(null=True, blank=True, verbose_name='Количество пор')
    average_pore_diameter = models.FloatField(null=True, blank=True, verbose_name='Средний диаметр пор (мкм)')
    total_pore_area = models.FloatField(null=True, blank=True, verbose_name='Общая площадь пор (мкм²)')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(null=True, blank=True, verbose_name='Сообщение об ошибке')
    
    # Путь к результирующим файлам
    results_directory = models.CharField(max_length=500, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Анализ пористости'
        verbose_name_plural = 'Анализы пористости'
        ordering = ['-created_at']


class PorosityImage(models.Model):
    """Модель для хранения изображений анализа"""
    
    analysis = models.ForeignKey(PorosityAnalysis, on_delete=models.CASCADE, related_name='images')
    original_image = models.ImageField(upload_to='porosity/images/', verbose_name='Исходное изображение')
    filename = models.CharField(max_length=255, verbose_name='Имя файла')
    
    # Результаты для конкретного изображения
    image_porosity_percentage = models.FloatField(null=True, blank=True)
    image_number_of_pores = models.IntegerField(null=True, blank=True)
    image_average_pore_diameter = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Изображение анализа пористости'
        verbose_name_plural = 'Изображения анализа пористости'


class PorosityResults(models.Model):
    """Модель для детальных результатов анализа"""
    
    analysis = models.OneToOneField(PorosityAnalysis, on_delete=models.CASCADE, related_name='detailed_results')
    
    # JSON поля для хранения детальных данных
    pore_size_distribution = models.JSONField(null=True, blank=True, verbose_name='Распределение размеров пор')
    interpore_distances = models.JSONField(null=True, blank=True, verbose_name='Межпоровые расстояния')
    pore_orientation = models.JSONField(null=True, blank=True, verbose_name='Ориентация пор')
    pore_shapes = models.JSONField(null=True, blank=True, verbose_name='Формы пор')
    
    # Статистические данные
    scale_info = models.JSONField(null=True, blank=True, verbose_name='Информация о масштабе')
    excluded_areas = models.JSONField(null=True, blank=True, verbose_name='Исключенные области')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Детальные результаты анализа'
        verbose_name_plural = 'Детальные результаты анализов'


class PorosityVisualization(models.Model):
    """Модель для хранения путей к файлам визуализации"""
    
    VISUALIZATION_TYPES = [
        ('scale_bar', 'Область шкалы'),
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
    
    analysis = models.ForeignKey(PorosityAnalysis, on_delete=models.CASCADE, related_name='visualizations')
    visualization_type = models.CharField(max_length=50, choices=VISUALIZATION_TYPES)
    file_path = models.CharField(max_length=500, verbose_name='Путь к файлу')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Визуализация анализа'
        verbose_name_plural = 'Визуализации анализов'
        unique_together = ['analysis', 'visualization_type']