from celery import shared_task
from src.modules.bi_analysis.services.sync import sync_from_sources

@shared_task
def sync_data_from_sources():
    try:
        sync_data_from_sources()  # Выполняем синхронизацию данных
        return "Обновление данных успешно завершено."
    except Exception as e:
        return f"Обновление данных прервано по причине: {str(e)}"