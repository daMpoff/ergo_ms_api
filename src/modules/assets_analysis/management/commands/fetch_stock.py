import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

try:
    from src.modules.assets_analysis.scripts import fetch_historical_stock_prices, SELECTED_STOCKS
except ImportError:
    def fetch_historical_stock_prices(*args, **kwargs):
        raise ImportError("Не удалось импортировать 'fetch_historical_stock_prices'.")

logger = logging.getLogger(__name__)

DEFAULT_DAYS_TO_FETCH = 30

class Command(BaseCommand):
    """
    Команда для получения исторических цен на акции (Tesla, Лукойл и др.)
    и сохранения их в базу данных.
    """
    help = (
        'Загружает исторические цены на акции с Yahoo Finance. '
        'Работает по диапазону дат (--start-date/--end-date) или за последние N дней (--days).'
    )

    def add_arguments(self, parser):
        """
        Определяет аргументы командной строки.
        """
        parser.add_argument(
            '--days',
            type=int,
            default=DEFAULT_DAYS_TO_FETCH,
            help=(
                f'За сколько последних дней загружать цены (по умолчанию: {DEFAULT_DAYS_TO_FETCH}). '
                f'Игнорируется, если указан --start-date.'
            )
        )
        parser.add_argument(
            '--start-date',
            type=str,
            default=None,
            help='Начальная дата для загрузки цен (YYYY-MM-DD). Переопределяет --days.'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            default=None,
            help='Конечная дата для загрузки цен (YYYY-MM-DD). Используется с --start-date. По умолчанию - сегодня.'
        )
        parser.add_argument(
            '--stocks',
            nargs='*',
            default=None,
            help=(
                'Список акций для загрузки (названия из настроек). '
                f"Доступны: {', '.join(SELECTED_STOCKS.keys()) if SELECTED_STOCKS else 'не найдены'}. "
                'По умолчанию: все доступные акции.'
            )
        )

    def handle(self, *args, **options):
        """
        Основная логика выполнения команды.
        """
        self.stdout.write(self.style.SUCCESS("--- Запуск загрузчика цен на акции ---"))

        # --- 1. Обработка и валидация аргументов ---
        start_date_str = options['start_date']
        end_date_str = options['end_date']
        days_delta = options['days']
        stocks_to_fetch = options['stocks']

        start_date_obj = None
        end_date_obj = None

        try:
            if start_date_str:
                self.stdout.write("[*] Режим: по диапазону дат.")
                start_date_obj = parse_date(start_date_str)
                if not start_date_obj:
                    raise ValueError("Неверный формат --start-date.")

                end_date_obj = parse_date(end_date_str) if end_date_str else datetime.now().date()
                if not end_date_obj:
                    raise ValueError("Неверный формат --end-date.")

                if start_date_obj > end_date_obj:
                    raise CommandError("Начальная дата (--start-date) не может быть позже конечной (--end-date).")
            else:
                self.stdout.write(f"[*] Режим: за последние {days_delta} дней.")
                end_date_obj = datetime.now().date()
                start_date_obj = end_date_obj - timedelta(days=days_delta)

            self.stdout.write(
                f"[*] Диапазон дат для загрузки: с {start_date_obj.strftime('%Y-%m-%d')} "
                f"по {end_date_obj.strftime('%Y-%m-%d')}."
            )

            if stocks_to_fetch:
                valid_stocks = []
                for stock_name in stocks_to_fetch:
                    if stock_name in SELECTED_STOCKS:
                        valid_stocks.append(stock_name)
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"[!] Акция '{stock_name}' не найдена в настройках и будет пропущена."))

                stocks_to_fetch = valid_stocks
                if not stocks_to_fetch:
                    self.stdout.write(
                        self.style.ERROR("[-] Не найдено ни одной валидной акции для загрузки. Завершение работы."))
                    return

                self.stdout.write(f"[*] Будут загружены данные для следующих акций: {', '.join(stocks_to_fetch)}")
            else:
                self.stdout.write("[*] Будут загружены данные для ВСЕХ акций из настроек.")

        except (ValueError, TypeError) as e:
            raise CommandError(f"Ошибка в датах: {e}. Используйте формат YYYY-MM-DD.")
        except CommandError as e:
            self.stderr.write(self.style.ERROR(f"Ошибка: {e}"))
            return

        # --- 2. Вызов основной функции-загрузчика ---
        try:
            self.stdout.write("\n[*] Процесс получения и сохранения данных...")

            fetch_historical_stock_prices(
                start_date=start_date_obj,
                end_date=end_date_obj,
                stocks=stocks_to_fetch
            )

            self.stdout.write(self.style.SUCCESS("\n--- Загрузка цен на акции успешно завершена ---"))

        except ImportError as e:
            self.stderr.write(self.style.ERROR(f"[!] КРИТИЧЕСКАЯ ОШИБКА ИМПОРТА: {e}"))
            self.stderr.write(self.style.ERROR("[!] Проверьте путь до 'data_loader.py' в коде команды."))
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в команде fetch_stock: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"\n[!] Произошла непредвиденная ошибка: {e}"))
            self.stderr.write(self.style.ERROR("[!] Подробности смотрите в логах."))