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
    segments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoAnalysis
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'original_video', 'audio_file', 'subtitles_file', 'output_video',
            'duration', 'duration_formatted', 'subtitle_count', 'segments_count', 'error_message',
            'subtitle_segments'
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