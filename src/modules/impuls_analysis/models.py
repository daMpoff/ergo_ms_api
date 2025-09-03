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
    
    # Результаты анализа
    analysis_results = models.JSONField(null=True, blank=True, verbose_name='Результаты анализа')
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    # Celery task
    task_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID задачи Celery')
    
    class Meta:
        verbose_name = 'Анализ импульса'
        verbose_name_plural = 'Анализы импульса'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
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
