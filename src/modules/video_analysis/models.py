import uuid
import os
from pathlib import Path

from django.db import models
from django.contrib.auth import get_user_model

from src.config.settings.static import MEDIA_ROOT

User = get_user_model()

class VideoAnalysis(models.Model):
    """
    Модель для хранения информации о видео-анализе
    """
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
    
    # Исходные файлы
    original_video = models.FileField(upload_to='video_analysis/original/', verbose_name='Исходное видео')
    
    # Статус и время
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Начало обработки')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершение обработки')
    
    # Результаты
    audio_file = models.FileField(upload_to='video_analysis/audio/', null=True, blank=True, verbose_name='Аудио файл')
    subtitles_file = models.FileField(upload_to='video_analysis/subtitles/', null=True, blank=True, verbose_name='Файл субтитров')
    output_video = models.FileField(upload_to='video_analysis/output/', null=True, blank=True, verbose_name='Видео с субтитрами')
    
    # Метаданные
    duration = models.FloatField(null=True, blank=True, verbose_name='Длительность (секунды)')
    subtitle_count = models.IntegerField(default=0, verbose_name='Количество субтитров')
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    # Celery task
    task_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID задачи Celery')
    
    class Meta:
        verbose_name = 'Видео-анализ'
        verbose_name_plural = 'Видео-анализы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def analysis_dir(self):
        """Возвращает путь к папке анализа"""
        return Path(MEDIA_ROOT) / 'video_analysis' / str(self.id)
    
    def get_analysis_dir(self):
        """Создает и возвращает папку для анализа"""
        analysis_dir = self.analysis_dir
        analysis_dir.mkdir(parents=True, exist_ok=True)
        return analysis_dir
    
    def get_original_video_path(self):
        """Возвращает путь к исходному видео"""
        return str(self.analysis_dir / 'original_video.mp4')
    
    def get_audio_path(self):
        """Возвращает путь к аудио файлу"""
        return str(self.analysis_dir / 'audio.wav')
    
    def get_subtitles_path(self):
        """Возвращает путь к файлу субтитров"""
        return str(self.analysis_dir / 'subtitles.srt')
    
    def get_output_video_path(self):
        """Возвращает путь к выходному видео"""
        return str(self.analysis_dir / 'output_video.mp4')
    
    def update_status(self, status, **kwargs):
        """Обновляет статус и связанные поля"""
        from django.utils import timezone
        
        self.status = status
        
        if status == 'processing' and not self.started_at:
            self.started_at = timezone.now()
        elif status in ['completed', 'failed'] and not self.completed_at:
            self.completed_at = timezone.now()
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.save()
    
    def cleanup_files(self):
        """Удаляет временные файлы"""
        try:
            if self.audio_file and os.path.exists(self.audio_file.path):
                os.remove(self.audio_file.path)
        except Exception:
            pass


class SubtitleSegment(models.Model):
    """
    Модель для хранения отдельных сегментов субтитров
    """
    video_analysis = models.ForeignKey(VideoAnalysis, on_delete=models.CASCADE, related_name='subtitle_segments', verbose_name='Видео-анализ')
    segment_number = models.IntegerField(verbose_name='Номер сегмента')
    start_time = models.CharField(max_length=20, verbose_name='Время начала')
    end_time = models.CharField(max_length=20, verbose_name='Время окончания')
    russian_text = models.TextField(verbose_name='Русский текст')
    french_text = models.TextField(verbose_name='Французский текст')
    
    class Meta:
        verbose_name = 'Сегмент субтитров'
        verbose_name_plural = 'Сегменты субтитров'
        ordering = ['segment_number']
    
    def __str__(self):
        return f"Сегмент {self.segment_number} ({self.start_time} - {self.end_time})" 