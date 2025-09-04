import os
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class ImpulsAnalysis(models.Model):
    """
    Модель для хранения информации об анализе импульса
    """
    ANALYSIS_TYPE_CHOICES = [
        ('standard', 'Стандартный анализ'),
        ('advanced', 'Расширенный анализ'),
        ('custom', 'Пользовательский анализ'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменен'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    analysis_type = models.CharField(
        max_length=20, 
        choices=ANALYSIS_TYPE_CHOICES, 
        default='standard', 
        verbose_name='Тип анализа'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name='Статус'
    )
    
    # Время создания и обновления
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Начало обработки')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершение обработки')
    
    # Параметры протокола
    protocol_number = models.CharField(max_length=64, null=True, blank=True, verbose_name='Номер протокола')
    p_static = models.FloatField(null=True, blank=True, verbose_name='Pст, %')
    energy_j = models.FloatField(null=True, blank=True, verbose_name='Энергия удара, Дж')
    
    
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    # Celery task
    task_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID задачи Celery')
    
    class Meta:
        verbose_name = 'Анализ импульса'
        verbose_name_plural = 'Анализы импульса'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    
    def delete_analysis_files(self):
        """Удаляет файлы анализа (изображения) по UUID"""
        import os
        from django.conf import settings
        
        files_deleted = 0
        
        # Ищем и удаляем изображения по UUID
        analysis_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'analyses')
        if os.path.exists(analysis_dir):
            for filename in os.listdir(analysis_dir):
                if filename.startswith(str(self.id)):
                    try:
                        file_path = os.path.join(analysis_dir, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            files_deleted += 1
                    except Exception:
                        pass
        
        return files_deleted
    
    def update_status(self, status, **kwargs):
        """Обновляет статус анализа"""
        self.status = status
        if status == 'processing' and not self.started_at:
            self.started_at = kwargs.get('started_at')
        elif status in ['completed', 'failed', 'cancelled'] and not self.completed_at:
            self.completed_at = kwargs.get('completed_at')
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.save()

class ImpulsFile(models.Model):
    """
    Модель для хранения файлов анализа импульса
    """
    FILE_TYPE_CHOICES = [
        ('force_calculation', 'Расчет силы'),
        ('experiment_plan', 'План эксперимента'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ImpulsAnalysis, 
        on_delete=models.CASCADE, 
        related_name='files',
        verbose_name='Анализ'
    )
    file_type = models.CharField(
        max_length=20, 
        choices=FILE_TYPE_CHOICES, 
        verbose_name='Тип файла'
    )
    file = models.FileField(
        upload_to='impuls_analysis/files/',
        verbose_name='Файл'
    )
    original_filename = models.CharField(
        max_length=255, 
        verbose_name='Оригинальное имя файла'
    )
    file_size = models.BigIntegerField(verbose_name='Размер файла (байт)')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Загружен')
    
    class Meta:
        verbose_name = 'Файл анализа импульса'
        verbose_name_plural = 'Файлы анализа импульса'
        unique_together = ['analysis', 'file_type']
    
    def __str__(self):
        return f"{self.analysis.title} - {self.get_file_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.file_size and self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

class ImpulsProtocol(models.Model):
    """
    Модель для хранения сгенерированных протоколов
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ImpulsAnalysis, 
        on_delete=models.CASCADE, 
        related_name='protocols',
        verbose_name='Анализ'
    )
    protocol_file = models.FileField(
        upload_to='impuls_analysis/protocols/',
        verbose_name='Файл протокола'
    )
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='Сгенерирован')
    file_size = models.BigIntegerField(verbose_name='Размер файла (байт)')
    
    class Meta:
        verbose_name = 'Протокол анализа импульса'
        verbose_name_plural = 'Протоколы анализа импульса'
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Протокол {self.analysis.title} от {self.generated_at.strftime('%d.%m.%Y %H:%M')}"
    
    def save(self, *args, **kwargs):
        if not self.file_size and self.protocol_file:
            self.file_size = self.protocol_file.size
        super().save(*args, **kwargs)


class ImpulsForceRecord(models.Model):
    """
    Запись замеров из файла "Расчет силы" (force_file)
    """
    id = models.AutoField(primary_key=True)
    sheet_title = models.CharField(max_length=255, verbose_name='Лист', blank=True, default='')
    protocol_number = models.CharField(max_length=64, verbose_name='Номер протокола')
    pct_static = models.FloatField(null=True, blank=True, verbose_name='Pст, %')
    v = models.FloatField(null=True, blank=True, verbose_name='v')
    p = models.FloatField(null=True, blank=True, verbose_name='p')
    f = models.FloatField(null=True, blank=True, verbose_name='f')
    energy_j = models.FloatField(null=True, blank=True, verbose_name='Энергия удара, Дж')
    velocity_ms = models.FloatField(null=True, blank=True, verbose_name='Скорость удара, м/с')
    force_n = models.FloatField(null=True, blank=True, verbose_name='Сила удара (P), Н')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Запись расчета силы'
        verbose_name_plural = 'Записи расчета силы'
        indexes = [
            models.Index(fields=['protocol_number']),
        ]


class ImpulsPlanRecord(models.Model):
    """
    Параметры протоколов из файла плана эксперимента (plan_file)
    """
    id = models.AutoField(primary_key=True)
    protocol_number = models.CharField(max_length=64, verbose_name='Номер протокола')
    p_static = models.FloatField(null=True, blank=True, verbose_name='Pст, %')
    p_static_value = models.FloatField(null=True, blank=True, verbose_name='Pст значение')
    l1_l2_ratio = models.IntegerField(null=True, blank=True, verbose_name='L1/L2')
    l1_m = models.FloatField(null=True, blank=True, verbose_name='L1 (м)')
    d1_m = models.FloatField(null=True, blank=True, verbose_name='d1 (м)')
    m1_kg = models.FloatField(null=True, blank=True, verbose_name='m1 (кг)')
    l2_m = models.FloatField(null=True, blank=True, verbose_name='L2 (м)')
    d2_m = models.FloatField(null=True, blank=True, verbose_name='d2 (м)')
    t_s = models.FloatField(null=True, blank=True, verbose_name='Т (с)')
    a_j = models.FloatField(null=True, blank=True, verbose_name='А, (Дж)')
    v_ms = models.FloatField(null=True, blank=True, verbose_name='V, (м/с)')
    c12_kg_s = models.FloatField(null=True, blank=True, verbose_name='С1,2 (кг/с)')
    p_n = models.FloatField(null=True, blank=True, verbose_name='Р, (Н)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Запись плана эксперимента'
        verbose_name_plural = 'Записи плана эксперимента'
        indexes = [
            models.Index(fields=['protocol_number']),
        ]


class ImpulsExtremum(models.Model):
    """
    Модель для хранения экстремумов (максимумов) импульсов
    """
    EXTREMUM_TYPE_CHOICES = [
        ('max', 'Максимум'),
        ('min', 'Минимум'),
    ]
    
    id = models.AutoField(primary_key=True)
    analysis = models.ForeignKey(
        ImpulsAnalysis, 
        on_delete=models.CASCADE, 
        related_name='extrema',
        verbose_name='Анализ'
    )
    pulse_id = models.IntegerField(verbose_name='Номер импульса')
    extremum_id = models.IntegerField(null=True, blank=True, verbose_name='Номер экстремума в импульсе')
    extremum_type = models.CharField(
        max_length=10, 
        choices=EXTREMUM_TYPE_CHOICES, 
        verbose_name='Тип экстремума'
    )
    
    # Координаты экстремума
    v = models.FloatField(null=True, blank=True, verbose_name='Время, с')
    f = models.FloatField(null=True, blank=True, verbose_name='Сила, Н')
    
    # Параметры импульса
    duration_v = models.FloatField(verbose_name='Длительность импульса, с')
    area = models.FloatField(verbose_name='Площадь импульса')
    v_start = models.FloatField(verbose_name='Время начала импульса, с')
    v_end = models.FloatField(verbose_name='Время окончания импульса, с')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Экстремум импульса'
        verbose_name_plural = 'Экстремумы импульса'
        ordering = ['analysis', 'pulse_id', 'extremum_id']
        indexes = [
            models.Index(fields=['analysis', 'pulse_id']),
            models.Index(fields=['analysis', 'extremum_type']),
        ]
    
    def __str__(self):
        return f"Экстремум {self.get_extremum_type_display()} в импульсе {self.pulse_id} (анализ {self.analysis.id})"