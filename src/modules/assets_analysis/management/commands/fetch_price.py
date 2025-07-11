import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from src.modules.assets_analysis.scripts import (
    SELECTED_COINS,
    SELECTED_ASSETS,
    SELECTED_STOCKS,
    fetch_historical_crypto_prices,
    fetch_historical_asset_prices,
    fetch_historical_stock_prices,
)

class Command(BaseCommand):
    help = "Получает цены криптовалют, курсы валют и/или котировки акций за указанный диапазон дат и сохраняет в БД"

    def add_arguments(self, parser):
        # --- Аргументы для дат ---
        parser.add_argument(
            '--start-date',
            type=str,
            required=True,
            help="Начальная дата в формате YYYY-MM-DD"
        )
        parser.add_argument(
            '--end-date',
            type=str,
            required=True,
            help="Конечная дата в формате YYYY-MM-DD"
        )
        # --- Аргумент --coins ---
        parser.add_argument(
            '--coins',
            nargs='+',
            default=[],
            help="Список монет для загрузки (если не указан, монеты не загружаются)"
        )
        # --- Аргумент --assets ---
        parser.add_argument(
            '--assets',
            nargs='+',
            default=[],
            help="Список валютных пар для загрузки (если не указан, валюты не загружаются)"
        )
        # --- Аргумент --stocks ---
        parser.add_argument(
            '--stocks',
            nargs='+',
            default=[],
            help="Список акций для загрузки (например, 'Tesla' 'Лукойл'). Если не указан, акции не загружаются."
        )


    def handle(self, *args, **options):
        start_date_str = options['start_date']
        end_date_str = options['end_date']
        coin_names = options['coins']
        asset_pairs = options['assets']
        stock_names = options['stocks']

        # --- Проверка, что хотя бы что-то выбрано для загрузки ---
        if not coin_names and not asset_pairs and not stock_names:
            self.stdout.write(self.style.ERROR("Ошибка: Необходимо указать хотя бы один из аргументов: --coins, --assets или --stocks."))
            return

        # --- Валидация и преобразование дат ---
        try:
            start_dt_naive = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt_naive = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            start_date_obj = start_dt_naive.date()
            end_date_obj = end_dt_naive.date()

            if start_date_obj > end_date_obj:
                 self.stdout.write(self.style.ERROR("Ошибка: Начальная дата не может быть позже конечной."))
                 return

            start_dt_aware_crypto = make_aware(datetime.datetime.combine(start_date_obj, datetime.time.min))
            end_dt_aware_crypto = make_aware(datetime.datetime.combine(end_date_obj, datetime.time.max))

        except ValueError:
            self.stdout.write(self.style.ERROR("Ошибка: Неверный формат даты. Используйте YYYY-MM-DD."))
            return

        # --- Загрузка криптовалют ---
        if coin_names:
            self.stdout.write(self.style.NOTICE(f"--- Обработка криптовалют ({', '.join(coin_names)}) ---"))
            coins_to_fetch = {}
            invalid_coins = []
            for coin in coin_names:
                if coin in SELECTED_COINS:
                    coins_to_fetch[coin] = SELECTED_COINS[coin]
                else:
                    invalid_coins.append(coin)

            if invalid_coins:
                self.stdout.write(self.style.WARNING(f"Предупреждение: Следующие монеты не настроены и будут пропущены: {', '.join(invalid_coins)}"))

            if not coins_to_fetch:
                self.stdout.write(self.style.ERROR(f"Ошибка: Не найдено валидных монет для загрузки из списка: {', '.join(coin_names)}."))
            else:
                self.stdout.write(self.style.NOTICE(f"Запрос цен для: {', '.join(coins_to_fetch.keys())}, период: {start_date_str} по {end_date_str}"))
                fetch_historical_crypto_prices(
                    start_date=start_dt_aware_crypto,
                    end_date=end_dt_aware_crypto,
                    coins=list(coins_to_fetch.keys())
                )
                self.stdout.write(self.style.SUCCESS(f"Обновление цен криптовалют для {', '.join(coins_to_fetch.keys())} завершено."))
        else:
             self.stdout.write(self.style.NOTICE("--- Пропуск загрузки криптовалют (--coins не указан) ---"))


        # --- Загрузка валют ---
        if asset_pairs:
            self.stdout.write(self.style.NOTICE(f"--- Обработка курсов валют ({', '.join(asset_pairs)}) ---"))
            assets_to_fetch = []
            invalid_assets = []
            for pair in asset_pairs:
                if pair in SELECTED_ASSETS:
                    assets_to_fetch.append(pair)
                else:
                    invalid_assets.append(pair)

            if invalid_assets:
                self.stdout.write(self.style.WARNING(f"Предупреждение: Следующие валютные пары не настроены и будут пропущены: {', '.join(invalid_assets)}"))

            if not assets_to_fetch:
                self.stdout.write(self.style.ERROR(f"Ошибка: Не найдено валидных валютных пар для загрузки из списка: {', '.join(asset_pairs)}."))
            else:
                self.stdout.write(self.style.NOTICE(f"Запрос курсов валют для: {', '.join(assets_to_fetch)}, период: {start_date_str} по {end_date_str}"))
                fetch_historical_asset_prices(
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    assets=assets_to_fetch
                )
                self.stdout.write(self.style.SUCCESS(f"Обновление курсов валют для {', '.join(assets_to_fetch)} завершено."))
        else:
             self.stdout.write(self.style.NOTICE("--- Пропуск загрузки курсов валют (--assets не указан) ---"))


        # --- Загрузка акций ---
        if stock_names:
            self.stdout.write(self.style.NOTICE(f"--- Обработка акций ({', '.join(stock_names)}) ---"))
            # Валидация акций
            stocks_to_fetch = {}
            invalid_stocks = []
            for stock_name in stock_names:
                if stock_name in SELECTED_STOCKS:
                    stocks_to_fetch[stock_name] = SELECTED_STOCKS[stock_name]
                else:
                    invalid_stocks.append(stock_name)

            if invalid_stocks:
                self.stdout.write(self.style.WARNING(f"Предупреждение: Следующие акции не настроены и будут пропущены: {', '.join(invalid_stocks)}"))

            if not stocks_to_fetch:
                self.stdout.write(self.style.ERROR(f"Ошибка: Не найдено валидных акций для загрузки из списка: {', '.join(stock_names)}."))
            else:
                self.stdout.write(self.style.NOTICE(f"Запрос котировок для: {', '.join(stocks_to_fetch.keys())}, период: {start_date_str} по {end_date_str}"))
                fetch_historical_stock_prices(
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    stocks=stocks_to_fetch
                )
                self.stdout.write(self.style.SUCCESS(f"Обновление котировок акций для {', '.join(stocks_to_fetch.keys())} завершено."))
        else:
             self.stdout.write(self.style.NOTICE("--- Пропуск загрузки акций (--stocks не указан) ---"))


        self.stdout.write(self.style.SUCCESS("\nКоманда fetch_price завершена."))