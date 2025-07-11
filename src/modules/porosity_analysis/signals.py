from django.db.models.signals import pre_delete
from django.dispatch import receiver
from src.modules.porosity_analysis.models import PorosityAnalysis
from src.modules.porosity_analysis.utils import cleanup_analysis_files
import logging

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=PorosityAnalysis)
def cleanup_analysis_files_on_delete(sender, instance, **kwargs):
    """
    Автоматическая очистка файлов при удалении анализа
    """
    try:
        cleanup_analysis_files(instance)
        logger.info(f"Файлы анализа {instance.id} очищены при удалении")
    except Exception as e:
        logger.error(f"Ошибка при очистке файлов анализа {instance.id}: {str(e)}") 