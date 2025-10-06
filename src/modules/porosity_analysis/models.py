import os
import uuid
from django.db import models
from django.utils import timezone


class PorosityGroup(models.Model):
    """Группа анализов пористости"""

    name = models.CharField(max_length=255, unique=True, verbose_name="Название группы")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        db_table = 'porosity_analysis_group'
        verbose_name = "Группа анализов пористости"
        verbose_name_plural = "Группы анализов пористости"
        ordering = ['name']

    def __str__(self):
        return self.name


class PorosityAnalysis(models.Model):
    """Модель для хранения результатов анализа пористости"""
    
    # Основная информация
    name = models.CharField(max_length=255, verbose_name="Название анализа")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    # Группа (необязательно)
    group = models.ForeignKey(
        'porosity_analysis.PorosityGroup',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='analyses',
        verbose_name="Группа"
    )
    # Времена выполнения
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="Время старта")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Время завершения")
    
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
    duration_seconds = models.IntegerField(null=True, blank=True, verbose_name="Длительность (сек)")
    
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
        # Приглушаем отладочный вывод в Celery
        
        if not os.path.exists(self.results_directory):
            pass
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
            # Подробный вывод отключен
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                result_files.append({
                    'name': filename,
                    'description': description,
                    'path': file_path,
                    'size_mb': file_size / (1024 * 1024)
                })
        
        # Подробный вывод отключен
        return result_files


class PorosityArchive(models.Model):
    """Модель для хранения информации о созданных архивах отчетов"""
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="UUID архива")
    name = models.CharField(max_length=255, verbose_name="Название архива")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    
    # Связь с анализами
    analyses = models.ManyToManyField(
        'porosity_analysis.PorosityAnalysis',
        related_name='archives',
        verbose_name="Анализы в архиве"
    )
    
    # Информация об архиве
    file_path = models.CharField(max_length=500, verbose_name="Путь к файлу архива")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="Размер файла (байты)")
    report_type = models.CharField(max_length=10, choices=[('pdf', 'PDF'), ('docx', 'Word')], default='docx', verbose_name="Тип отчета")
    
    # Статус создания
    STATUS_CHOICES = [
        ('creating', 'Создается'),
        ('completed', 'Создан'),
        ('failed', 'Ошибка'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='creating', verbose_name="Статус")
    error_message = models.TextField(blank=True, verbose_name="Сообщение об ошибке")
    
    class Meta:
        db_table = 'porosity_analysis_archive'
        verbose_name = "Архив отчетов пористости"
        verbose_name_plural = "Архивы отчетов пористости"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def file_size_mb(self):
        """Размер файла в мегабайтах"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    @property
    def analyses_count(self):
        """Количество анализов в архиве"""
        return self.analyses.count()
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    @property
    def is_creating(self):
        return self.status == 'creating'


class DownloadToken(models.Model):
    """Временный токен для скачивания файлов без авторизации"""
    
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Токен")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    expires_at = models.DateTimeField(verbose_name="Дата истечения")
    
    # Тип файла
    FILE_TYPE_CHOICES = [
        ('archive', 'Архив'),
        ('report', 'Отчет'),
        ('original', 'Исходное изображение'),
    ]
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, verbose_name="Тип файла")
    
    # ID объекта (analysis_id или archive_id)
    object_id = models.IntegerField(verbose_name="ID объекта")
    
    # Дополнительные параметры (например, тип отчета)
    params = models.JSONField(default=dict, blank=True, verbose_name="Параметры")
    
    # Использование
    is_used = models.BooleanField(default=False, verbose_name="Использован")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Время использования")
    
    class Meta:
        db_table = 'porosity_download_token'
        verbose_name = "Токен скачивания"
        verbose_name_plural = "Токены скачивания"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Token {self.token} ({self.file_type})"
    
    @property
    def is_expired(self):
        """Проверка истечения токена"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Проверка валидности токена"""
        return not self.is_used and not self.is_expired