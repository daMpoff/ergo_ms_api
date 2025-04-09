from datetime import datetime, timezone
from ..models import StagingGenericData
from .utils import clean_data, detect_outliers, normalize_data
from .alerts import send_alert_if_critical

def run_etl_for_record(record: StagingGenericData):
    """
    Выполняет полный ETL-процесс для одной записи сырой информации.
    """
    raw_data = record.raw_data

    # Этап 1: Очистка
    cleaned = clean_data(raw_data)

    # Этап 2: Обнаружение выбросов
    outliers = detect_outliers(cleaned)
    if outliers:
        send_alert_if_critical(record.source, outliers)

    # Этап 3: Нормализация
    normalized = normalize_data(cleaned)

    # Этап 4: Загрузка (здесь просто сохраняем результат в additional_info)
    record.additional_info = {
        "normalized": normalized,
        "outliers_detected": bool(outliers),
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    record.processed = True
    record.save()

    return record

def run_etl_for_all_unprocessed():
    """
    Выполняет ETL для всех необработанных записей.
    """
    for record in StagingGenericData.objects.filter(processed=False):
        run_etl_for_record(record)