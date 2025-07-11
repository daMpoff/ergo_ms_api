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
    
    def get_result_files(self):
        """Возвращает список файлов результатов анализа"""
        print(f"Checking results directory: {self.results_directory}")
        print(f"Directory exists: {os.path.exists(self.results_directory)}")
        
        if not os.path.exists(self.results_directory):
            print(f"Results directory does not exist: {self.results_directory}")
            return []
        
        result_files = []
        expected_files = [
            ('image_with_scale_bar.png', 'Изображение с обнаруженной шкалой'),
            ('scale_bar.png', 'Область шкалы'),
            ('figure1_contrast.png', 'Этапы обработки контраста'),
            ('figure2_excluded_areas.png', 'Исключенные области'),
            ('figure3_texture_clusters.png', 'Текстурный анализ'),
            ('figure4_mask_result.png', 'Бинарная маска и результат'),
            ('figure5_overlay.png', 'Наложение результатов'),
            ('pore_size_distribution.png', 'Распределение размеров пор'),
            ('interpore_distances.png', 'Межпоровые расстояния'),
            ('pore_orientation_rose.png', 'Роза направлений'),
            ('pore_orientation_histogram.png', 'Гистограмма ориентации'),
            ('pore_shapes_analysis.png', 'Анализ форм пор'),
            ('circularity_distribution.png', 'Распределение кругового фактора'),
            ('ellipticity_vs_area.png', 'Эллиптичность vs площадь')
        ]
        
        for filename, description in expected_files:
            file_path = os.path.join(self.results_directory, filename)
            print(f"Checking file: {file_path}, exists: {os.path.exists(file_path)}")
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                result_files.append({
                    'name': filename,
                    'description': description,
                    'path': file_path,
                    'size_mb': file_size / (1024 * 1024)
                })
        
        print(f"Found {len(result_files)} result files")
        return result_files