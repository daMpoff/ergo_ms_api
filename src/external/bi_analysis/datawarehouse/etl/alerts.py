import logging

logger = logging.getLogger(__name__)

def send_alert_if_critical(source: str, outliers: list[dict]):
    """
    Если найдены выбросы — логирует предупреждение.
    """
    if not outliers:
        return

    logger.warning(
        f"[ALERT] В источнике '{source}' обнаружены выбросы ({len(outliers)}): {outliers}"
    )