from rest_framework import serializers

from src.modules.video_analysis.models import VideoAnalysis, SubtitleSegment


class SubtitleSegmentSerializer(serializers.ModelSerializer):
    """Сериализатор для сегментов субтитров"""
    
    class Meta:
        model = SubtitleSegment
        fields = ['segment_number', 'start_time', 'end_time', 'russian_text', 'french_text']


class VideoAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для видео-анализа"""
    subtitle_segments = SubtitleSegmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    processing_time_seconds = serializers.SerializerMethodField()
    processing_time_formatted = serializers.SerializerMethodField()
    segments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoAnalysis
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'original_video', 'audio_file', 'subtitles_file', 'output_video',
            'duration', 'duration_formatted', 'processing_time_seconds', 'processing_time_formatted', 'subtitle_count', 'segments_count', 'error_message',
            'subtitle_segments', 'subtitle_lines_count', 'subtitle_font_size', 
            'subtitle_font_color', 'subtitle_background_color', 'subtitle_background_transparent',
            'subtitle_alignment', 'subtitle_margin_vertical', 'subtitle_margin_horizontal',
            'tts_enabled', 'tts_volume', 'tts_language', 'tts_voice_model', 'tts_audio_file'
        ]
        read_only_fields = fields
    
    def get_duration_formatted(self, obj):
        """Форматирует длительность в читаемый вид"""
        if not obj.duration:
            return None
        
        hours = int(obj.duration // 3600)
        minutes = int((obj.duration % 3600) // 60)
        seconds = int(obj.duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_segments_count(self, obj):
        """Возвращает количество сегментов субтитров"""
        return obj.subtitle_segments.count() if hasattr(obj, 'subtitle_segments') else 0

    def get_processing_time_seconds(self, obj):
        """Возвращает время обработки (секунды) как разницу completed_at - started_at"""
        try:
            if obj.started_at and obj.completed_at:
                delta = obj.completed_at - obj.started_at
                return int(delta.total_seconds())
        except Exception:
            pass
        return None

    def get_processing_time_formatted(self, obj):
        """Форматирует время обработки в HH:MM:SS или MM:SS"""
        seconds = self.get_processing_time_seconds(obj)
        if seconds is None:
            return None
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"


class BulkVideoAnalysisCreateSerializer(serializers.Serializer):
    """Сериализатор для создания нескольких анализов одновременно"""
    videos = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        max_length=10,  # Ограничиваем до 10 файлов за раз
        help_text="Список видео файлов для анализа"
    )
    titles = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True),
        required=False,
        help_text="Список названий для анализов (опционально)"
    )
    subtitle_lines_count = serializers.IntegerField(
        default=1, 
        min_value=1, 
        max_value=3,
        help_text="Количество строк субтитров одновременно (1-3)"
    )
    subtitle_font_size = serializers.IntegerField(
        default=24, 
        min_value=12, 
        max_value=72,
        help_text="Размер шрифта субтитров (12-72)"
    )
    subtitle_font_color = serializers.CharField(
        default='#FFFFFF', 
        max_length=7,
        help_text="Цвет шрифта субтитров в формате HEX (#FFFFFF)"
    )
    subtitle_background_color = serializers.CharField(
        default='#000000', 
        max_length=7,
        help_text="Цвет фона субтитров в формате HEX (#000000)"
    )
    subtitle_background_transparent = serializers.BooleanField(
        default=True,
        help_text="Прозрачный фон субтитров"
    )
    subtitle_alignment = serializers.ChoiceField(
        choices=['1', '2', '3', '4', '5', '6', '7', '8', '9'],
        default='2',
        help_text="Позиция субтитров"
    )
    subtitle_margin_vertical = serializers.IntegerField(
        default=20,
        min_value=0,
        max_value=200,
        help_text="Отступ по вертикали (в пикселях)"
    )
    subtitle_margin_horizontal = serializers.IntegerField(
        default=0,
        min_value=-200,
        max_value=200,
        help_text="Отступ по горизонтали (в пикселях)"
    )
    
    # Настройки озвучки
    tts_enabled = serializers.BooleanField(
        default=False,
        help_text="Включить озвучку"
    )
    tts_volume = serializers.FloatField(
        default=0.7,
        min_value=0.0,
        max_value=1.0,
        help_text="Громкость озвучки (0.0-1.0)"
    )
    tts_language = serializers.ChoiceField(
        choices=[('ru', 'Русский'), ('fr', 'Французский')],
        default='fr',
        help_text="Язык озвучки"
    )
    tts_voice_model = serializers.CharField(
        default='silero_tts',
        max_length=50,
        help_text="Модель голоса"
    )
    
    def validate(self, data):
        videos = data.get('videos', [])
        titles = data.get('titles', [])
        
        if titles and len(titles) != len(videos):
            raise serializers.ValidationError(
                "Количество названий должно соответствовать количеству видео файлов"
            )
        
        return data


class VideoAnalysisUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления анализа"""
    
    class Meta:
        model = VideoAnalysis
        fields = ['title', 'description']
    
    def validate_title(self, value):
        """Валидация названия"""
        if not value or not value.strip():
            raise serializers.ValidationError("Название не может быть пустым")
        return value.strip()


class VideoAnalysisCreateSerializer(serializers.Serializer):
    """Сериализатор для создания одного анализа"""
    video = serializers.FileField(help_text="Видео файл для анализа")
    title = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_blank=True,
        help_text="Название анализа (опционально)"
    )
    subtitle_lines_count = serializers.IntegerField(
        default=1, 
        min_value=1, 
        max_value=3,
        help_text="Количество строк субтитров одновременно (1-3)"
    )
    subtitle_font_size = serializers.IntegerField(
        default=24, 
        min_value=12, 
        max_value=72,
        help_text="Размер шрифта субтитров (12-72)"
    )
    subtitle_font_color = serializers.CharField(
        default='#FFFFFF', 
        max_length=7,
        help_text="Цвет шрифта субтитров в формате HEX (#FFFFFF)"
    )
    subtitle_background_color = serializers.CharField(
        default='#000000', 
        max_length=7,
        help_text="Цвет фона субтитров в формате HEX (#000000)"
    )
    subtitle_background_transparent = serializers.BooleanField(
        default=True,
        help_text="Прозрачный фон субтитров"
    )
    subtitle_alignment = serializers.ChoiceField(
        choices=['1', '2', '3', '4', '5', '6', '7', '8', '9'],
        default='2',
        help_text="Позиция субтитров"
    )
    subtitle_margin_vertical = serializers.IntegerField(
        default=20,
        min_value=0,
        max_value=200,
        help_text="Отступ по вертикали (в пикселях)"
    )
    subtitle_margin_horizontal = serializers.IntegerField(
        default=0,
        min_value=-200,
        max_value=200,
        help_text="Отступ по горизонтали (в пикселях)"
    )
    
    # Настройки озвучки
    tts_enabled = serializers.BooleanField(
        default=False,
        help_text="Включить озвучку"
    )
    tts_volume = serializers.FloatField(
        default=0.7,
        min_value=0.0,
        max_value=1.0,
        help_text="Громкость озвучки (0.0-1.0)"
    )
    tts_language = serializers.ChoiceField(
        choices=[('ru', 'Русский'), ('fr', 'Французский')],
        default='fr',
        help_text="Язык озвучки"
    )
    tts_voice_model = serializers.CharField(
        default='silero_tts',
        max_length=50,
        help_text="Модель голоса"
    )