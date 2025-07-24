import shutil

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from src.modules.video_analysis.models import VideoAnalysis


@receiver(pre_delete, sender=VideoAnalysis)
def cleanup_video_analysis_files(sender, instance, **kwargs):
    """
    Удаляет файлы и папки при удалении видео-анализа
    """
    try:
        # Удаляем папку анализа
        analysis_dir = instance.analysis_dir
        if analysis_dir.exists():
            shutil.rmtree(analysis_dir)
    except Exception as e:
        print(f"Ошибка при удалении файлов анализа {instance.id}: {e}") 