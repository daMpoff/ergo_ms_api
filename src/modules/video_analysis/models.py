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
    
    # Результаты (пути к файлам в папке results)
    audio_file = models.CharField(max_length=500, null=True, blank=True, verbose_name='Путь к аудио файлу')
    subtitles_file = models.CharField(max_length=500, null=True, blank=True, verbose_name='Путь к файлу субтитров')
    output_video = models.CharField(max_length=500, null=True, blank=True, verbose_name='Путь к видео с субтитрами')
    
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
        """Возвращает путь к папке анализа в results"""
        return Path(MEDIA_ROOT) / 'video_analysis' / 'results' / str(self.id)
    
    def get_analysis_dir(self):
        """Создает и возвращает папку для анализа"""
        analysis_dir = self.analysis_dir
        analysis_dir.mkdir(parents=True, exist_ok=True)
        return analysis_dir
    
    def get_original_video_path(self):
        """Возвращает путь к исходному видео"""
        return str(Path(MEDIA_ROOT) / 'video_analysis' / 'initial_video' / f'{self.title}.mp4')
    
    def get_audio_path(self):
        """Возвращает путь к аудио файлу"""
        if self.audio_file:
            return str(Path(MEDIA_ROOT) / self.audio_file)
        return None
    
    def get_subtitles_path(self):
        """Возвращает путь к файлу субтитров"""
        if self.subtitles_file:
            return str(Path(MEDIA_ROOT) / self.subtitles_file)
        return None
    
    def get_output_video_path(self):
        """Возвращает путь к выходному видео"""
        if self.output_video:
            return str(Path(MEDIA_ROOT) / self.output_video)
        return None
    
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
        """Удаляет всю папку с результатами анализа"""
        try:
            import shutil
            if self.analysis_dir.exists():
                shutil.rmtree(self.analysis_dir)
        except Exception:
            pass
    
    def get_subtitle_segments_data(self):
        """Возвращает данные сегментов субтитров в удобном формате"""
        segments = self.subtitle_segments.all().order_by('segment_number')
        return [
            {
                'segment_number': segment.segment_number,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'russian_text': segment.russian_text,
                'french_text': segment.french_text
            }
            for segment in segments
        ]
    
    def get_subtitle_segments_count(self):
        """Возвращает количество сегментов субтитров"""
        return self.subtitle_segments.count()
    
    def clear_subtitle_segments(self):
        """Удаляет все сегменты субтитров для данного анализа"""
        deleted_count = self.subtitle_segments.count()
        self.subtitle_segments.all().delete()
        return deleted_count
    
    def add_subtitle_segment(self, segment_number, start_time, end_time, russian_text, french_text):
        """Добавляет новый сегмент субтитров"""
        return SubtitleSegment.objects.create(
            video_analysis=self,
            segment_number=segment_number,
            start_time=start_time,
            end_time=end_time,
            russian_text=russian_text,
            french_text=french_text
        )


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