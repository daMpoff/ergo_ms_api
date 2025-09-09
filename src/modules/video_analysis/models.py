import uuid
import os
import logging
from pathlib import Path

from django.db import models
from django.contrib.auth import get_user_model

from src.config.settings.static import MEDIA_ROOT

# Получаем логгер для модуля
logger = logging.getLogger('video_analysis')

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
    
    # Настройки субтитров
    subtitle_lines_count = models.IntegerField(default=1, verbose_name='Количество строк субтитров одновременно')
    subtitle_font_size = models.IntegerField(default=24, verbose_name='Размер шрифта субтитров')
    subtitle_font_color = models.CharField(max_length=7, default='#FFFFFF', verbose_name='Цвет шрифта субтитров')
    subtitle_background_color = models.CharField(max_length=7, default='#000000', verbose_name='Цвет фона субтитров')
    subtitle_background_transparent = models.BooleanField(default=False, verbose_name='Прозрачный фон субтитров')
    
    # Позиционирование субтитров
    ALIGNMENT_CHOICES = [
        ('bottom', 'Снизу'),
        ('top', 'Сверху'),
        ('center', 'По центру'),
        ('custom', 'Пользовательское'),
    ]
    subtitle_alignment = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES, default='bottom', verbose_name='Выравнивание субтитров')
    subtitle_margin_vertical = models.IntegerField(default=20, verbose_name='Отступ по вертикали (в пикселях)')
    subtitle_margin_horizontal = models.IntegerField(default=0, verbose_name='Отступ по горизонтали (в пикселях)')
    
    # Настройки озвучки
    tts_enabled = models.BooleanField(default=False, verbose_name='Включить озвучку')
    tts_volume = models.FloatField(default=0.7, verbose_name='Громкость озвучки (0.0-1.0)')
    tts_language = models.CharField(max_length=10, default='fr', verbose_name='Язык озвучки', 
                                   help_text='ru - русский, fr - французский')
    tts_voice_model = models.CharField(max_length=50, default='silero_tts', verbose_name='Модель голоса')
    
    # Результат озвучки
    tts_audio_file = models.CharField(max_length=500, null=True, blank=True, verbose_name='Путь к файлу озвучки')
    
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
        if self.original_video:
            return str(Path(MEDIA_ROOT) / self.original_video)
        # Fallback на старую логику для совместимости
        return str(Path(MEDIA_ROOT) / 'video_analysis' / 'initial_video' / f'{self.id}.mp4')
    
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
    
    def get_tts_audio_path(self):
        """Возвращает путь к файлу озвучки"""
        if self.tts_audio_file:
            return str(Path(MEDIA_ROOT) / self.tts_audio_file)
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
        """Удаляет всю папку с результатами анализа и исходный видео файл по UUID"""
        try:
            import shutil
            from src.config.settings.static import MEDIA_ROOT
            
            # Удаляем папку с результатами
            if self.analysis_dir.exists():
                shutil.rmtree(self.analysis_dir)
                logger.debug(f"Удалена папка с результатами: {self.analysis_dir}")
            
            # Удаляем исходный видео файл по UUID
            if self.original_video:
                # Путь к исходному файлу уже сохранен в модели
                original_video_path = Path(MEDIA_ROOT) / self.original_video
                if original_video_path.exists():
                    original_video_path.unlink()
                    logger.debug(f"Удален исходный видео файл по UUID: {original_video_path}")
                else:
                    logger.warning(f"Исходный видео файл не найден: {original_video_path}")
            else:
                # Fallback: пытаемся удалить по UUID + расширение
                media_root = Path(MEDIA_ROOT)
                initial_dir = media_root / 'video_analysis' / 'initial_video'
                
                # Ищем файлы с UUID в имени
                for file_path in initial_dir.glob(f"{self.id}.*"):
                    try:
                        file_path.unlink()
                        logger.debug(f"Удален исходный файл по UUID (fallback): {file_path}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить файл {file_path}: {e}")
                        
        except Exception as e:
            logger.warning(f"Ошибка при удалении файлов анализа {self.id}: {e}")
    
    def force_cleanup_all_files(self):
        """Принудительно удаляет все файлы, связанные с анализом, по UUID"""
        try:
            import shutil
            from src.config.settings.static import MEDIA_ROOT
            
            media_root = Path(MEDIA_ROOT)
            
            # 1. Удаляем папку с результатами
            if self.analysis_dir.exists():
                shutil.rmtree(self.analysis_dir)
                logger.debug(f"Удалена папка с результатами: {self.analysis_dir}")
            
            # 2. Удаляем исходный видео файл по UUID
            initial_dir = media_root / 'video_analysis' / 'initial_video'
            
            # Ищем все файлы, начинающиеся с UUID
            uuid_pattern = f"{self.id}.*"
            found_files = list(initial_dir.glob(uuid_pattern))
            
            if found_files:
                for file_path in found_files:
                    try:
                        file_path.unlink()
                        logger.debug(f"Удален исходный файл по UUID: {file_path}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить файл {file_path}: {e}")
            else:
                logger.info(f"Файлы с UUID {self.id} не найдены в {initial_dir}")
            
            # 3. Проверяем, есть ли файлы в других местах
            # Ищем во всех подпапках video_analysis
            video_analysis_root = media_root / 'video_analysis'
            if video_analysis_root.exists():
                for root, dirs, files in os.walk(video_analysis_root):
                    for file in files:
                        if file.startswith(str(self.id)):
                            file_path = Path(root) / file
                            try:
                                file_path.unlink()
                                logger.debug(f"Удален файл по UUID из {root}: {file}")
                            except Exception as e:
                                logger.warning(f"Не удалось удалить файл {file_path}: {e}")
                                
        except Exception as e:
            logger.error(f"Критическая ошибка при принудительной очистке файлов анализа {self.id}: {e}")
            raise
    
    @classmethod
    def cleanup_orphaned_files(cls):
        """Очищает осиротевшие файлы - файлы без привязки к анализам"""
        try:
            from src.config.settings.static import MEDIA_ROOT
            import os
            
            media_root = Path(MEDIA_ROOT)
            initial_dir = media_root / 'video_analysis' / 'initial_video'
            
            if not initial_dir.exists():
                return
            
            # Получаем все UUID анализов из БД
            existing_uuids = set(str(analysis.id) for analysis in cls.objects.all())
            
            # Ищем файлы в папке initial_video
            orphaned_files = []
            for file_path in initial_dir.iterdir():
                if file_path.is_file():
                    # Извлекаем UUID из имени файла (убираем расширение)
                    file_uuid = file_path.stem
                    
                    # Проверяем, есть ли такой UUID в БД
                    if file_uuid not in existing_uuids:
                        orphaned_files.append(file_path)
            
            # Удаляем осиротевшие файлы
            deleted_count = 0
            for file_path in orphaned_files:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Удален осиротевший файл: {file_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить осиротевший файл {file_path}: {e}")
            
            logger.info(f"Очистка осиротевших файлов завершена. Удалено: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке осиротевших файлов: {e}")
            return 0
    
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