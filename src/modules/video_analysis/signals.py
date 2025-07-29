import shutil

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from src.modules.video_analysis.models import VideoAnalysis


@receiver(pre_delete, sender=VideoAnalysis)
def cleanup_video_analysis_files(sender, instance, **kwargs):
    """
    Удаляет файлы, папки и сегменты при удалении видео-анализа
    """
    try:
        # Удаляем сегменты субтитров (они удалятся автоматически из-за CASCADE)
        segments_count = instance.get_subtitle_segments_count()
        if segments_count > 0:
            print(f"Удаление {segments_count} сегментов субтитров для анализа {instance.id}")
        
        # Удаляем папку анализа
        analysis_dir = instance.analysis_dir
        if analysis_dir.exists():
            shutil.rmtree(analysis_dir)
            print(f"Удалена папка анализа {instance.id}")
    except Exception as e:
        print(f"Ошибка при удалении файлов анализа {instance.id}: {e}") 