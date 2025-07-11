import requests
import datetime
import time

import yfinance as yf

import xml.etree.ElementTree as ET

from decimal import Decimal, InvalidOperation, DivisionByZero

from django.utils.timezone import make_aware, timezone, is_aware
from django.db import transaction
from django.conf import settings

from src.modules.assets_analysis.models import CryptoPrice, AssetPrice, StockPrice

# Настройки для Криптовалют
DEFAULT_CRYPTO_SOURCE = "auto" # auto, binance, coingecko
SELECTED_COINS = {
    "bitcoin": {"binance": "BTCUSDT", "coingecko": "bitcoin"},
    "ethereum": {"binance": "ETHUSDT", "coingecko": "ethereum"},
    "bnb": {"binance": "BNBUSDT", "coingecko": "binancecoin"},
    "xrp": {"binance": "XRPUSDT", "coingecko": "ripple"},
    "cardano": {"binance": "ADAUSDT", "coingecko": "cardano"},
    "dogecoin": {"binance": "DOGEUSDT", "coingecko": "dogecoin"},
    "solana": {"binance": "SOLUSDT", "coingecko": "solana"},
    "polkadot": {"binance": "DOTUSDT", "coingecko": "polkadot"},
    "tron": {"binance": "TRXUSDT", "coingecko": "tron"},
    "litecoin": {"binance": "LTCUSDT", "coingecko": "litecoin"},
}

# Настройки для валют
DEFAULT_ASSET_SOURCE = "cbrf"
DEFAULT_USD_RATE_SOURCE = "frankfurter"
SELECTED_ASSETS = {
    "USD/RUB": {"cbrf_id": "R01235"},  # Доллар США
    "EUR/RUB": {"cbrf_id": "R01239"},  # Евро
    "CNY/RUB": {"cbrf_id": "R01375"},  # Китайский юань
    "GBP/RUB": {"cbrf_id": "R01035"},  # Фунт стерлингов
    "KZT/RUB": {"cbrf_id": "R01335"},  # Казахстанский тенге
}

# --- Настройки для Акций ---
SELECTED_STOCKS = {
    'Tesla': {
        'ticker': 'TSLA',
        'currency': 'USD',
        'source': 'yfinance'
    },
    'Лукойл': {
        'ticker': 'LKOH',
        'currency': 'RUB',
        'source': 'moex'
    },
}
def fetch_from_binance(symbol, start_date, end_date):
    """
    Получает исторические данные (High price) с Binance для заданного диапазона дат.
    start_date и end_date должны быть timezone-aware datetime объектами (предпочтительно UTC).
    """
    limit = 1000
    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    all_data = []
    current_start_ts = start_ts

    while current_start_ts < end_ts:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&startTime={current_start_ts}&endTime={end_ts}&limit={limit}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data: break
            chunk_data = []
            last_timestamp_ms = 0
            for item in data:
                open_time_ms = int(item[0])
                if open_time_ms < end_ts:
                    timestamp = make_aware(datetime.datetime.utcfromtimestamp(open_time_ms / 1000),
                                           timezone=datetime.timezone.utc)
                    high_price = Decimal(item[2])
                    chunk_data.append((timestamp, high_price))
                    last_timestamp_ms = open_time_ms
            if not chunk_data: break
            all_data.extend(chunk_data)
            current_start_ts = last_timestamp_ms + 1
            if len(data) < limit: break
            time.sleep(0.2)
        except requests.exceptions.RequestException as e:
            print(f"[-] Ошибка сети при запросе к Binance ({symbol}): {e}")
            return None
        except Exception as e:
            print(f"[-] Неожиданная ошибка при обработке данных Binance ({symbol}): {e}")
            return None
    return all_data


def fetch_from_coingecko(coin, start_date, end_date):
    """
    Получает исторические данные с CoinGecko для заданного диапазона дат.
    start_date и end_date должны быть timezone-aware datetime объектами.
    """
    start_ts = int(start_date.timestamp())
    end_ts = int((end_date + datetime.timedelta(days=1)).timestamp())
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart/range?vs_currency=usd&from={start_ts}&to={end_ts}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        if not prices:
            print(f"[*] [CoinGecko] Нет данных для {coin} за период {start_date.date()} - {end_date.date()}")
            return []

        processed_prices = []
        for ts_ms, price in prices:
            dt_utc = make_aware(datetime.datetime.utcfromtimestamp(ts_ms / 1000), timezone=datetime.timezone.utc)
            record_dt = dt_utc
            if dt_utc.time() == datetime.time(0, 0, 0):
                record_dt = dt_utc - datetime.timedelta(microseconds=1)

            if start_date.date() <= record_dt.date() <= end_date.date():
                processed_prices.append((record_dt, Decimal(price)))

        processed_prices.sort(key=lambda x: x[0])
        return processed_prices

    except requests.exceptions.Timeout:
        print(f"[-] Тайм-аут при запросе к CoinGecko ({coin})")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[-] Ошибка сети при запросе к CoinGecko ({coin}): {e}")
        return None
    except Exception as e:
        print(f"[-] Неожиданная ошибка при обработке данных CoinGecko ({coin}): {e}")
        return None

def get_prices(coin, start_date, end_date, source):
    api_names = SELECTED_COINS.get(coin)
    if not api_names:
        print(f"[!] Не найдены API имена для монеты: {coin}")
        return None

    if source == "binance":
        print(f"[*] Запрос {coin} с Binance...")
        return fetch_from_binance(api_names["binance"], start_date, end_date)
    elif source == "coingecko":
        print(f"[*] Запрос {coin} с CoinGecko...")
        return fetch_from_coingecko(api_names["coingecko"], start_date, end_date)
    elif source == "auto":
        print(f"[*] Запрос {coin} с Binance (auto)...")
        data = fetch_from_binance(api_names["binance"], start_date, end_date)
        if data is None:
            print(f"[!] Ошибка при запросе к Binance для {coin}, пробую CoinGecko (auto)...")
            data = fetch_from_coingecko(api_names["coingecko"], start_date, end_date)
        elif not data:
            print(f"[*] Binance не вернул данных для {coin}, пробую CoinGecko (auto)...")
            data = fetch_from_coingecko(api_names["coingecko"], start_date, end_date)
        return data
    else:
        print(f"[!] Неизвестный источник: {source}")
        return None


def fetch_historical_crypto_prices(start_date, end_date, coins=None, source=DEFAULT_CRYPTO_SOURCE):
    if coins is None:
        coins = list(SELECTED_COINS.keys())

    start_dt_utc = make_aware(
        datetime.datetime.combine(start_date if isinstance(start_date, datetime.date) else start_date.date(),
                                  datetime.time.min), timezone=datetime.timezone.utc)
    end_dt_utc = make_aware(
        datetime.datetime.combine(end_date if isinstance(end_date, datetime.date) else end_date.date(),
                                  datetime.time.max), timezone=datetime.timezone.utc)

    deleted_count, _ = CryptoPrice.objects.filter(
        name__in=list(coins),
        timestamp__gte=start_dt_utc,
        timestamp__lte=end_dt_utc
    ).delete()
    print(
        f"[Crypto] Удалено {deleted_count} старых записей криптовалют ({', '.join(coins)}) для диапазона {start_dt_utc.date()} - {end_dt_utc.date()}")

    total_added = 0
    for coin in coins:
        prices = get_prices(coin, start_dt_utc, end_dt_utc, source)
        if prices is not None:
            if prices:
                objects_to_create = []
                unique_keys = set()
                for ts, price in prices:
                    if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) != datetime.timedelta(0):
                        ts = make_aware(ts.replace(tzinfo=None),
                                        timezone=datetime.timezone.utc) if ts.tzinfo else make_aware(ts,
                                                                                                     timezone=datetime.timezone.utc)
                        ts = ts.astimezone(datetime.timezone.utc)

                    if start_dt_utc <= ts <= end_dt_utc:
                        key = (coin, ts.date())
                        if key not in unique_keys:
                            objects_to_create.append(CryptoPrice(name=coin, price_usd=price, timestamp=ts))
                            unique_keys.add(key)

                if objects_to_create:
                    try:
                        objects_to_create.sort(key=lambda x: x.timestamp)
                        created_objects = CryptoPrice.objects.bulk_create(objects_to_create, ignore_conflicts=True)
                        num_actually_created = len(created_objects)
                        print(
                            f"[+] [Crypto] Добавлено {num_actually_created} записей для {coin} (запрошено {len(objects_to_create)})")
                        total_added += num_actually_created
                    except Exception as e:
                        print(f"[-] [Crypto] Ошибка bulk_create для {coin}: {e}")
                else:
                    print(f"[*] [Crypto] Нет новых данных для {coin} в указанном диапазоне после фильтрации.")
            else:
                print(f"[*] [Crypto] Нет исторических данных для {coin} от источника {source}.")
        else:
            print(f"[-] [Crypto] Не удалось получить исторические данные для {coin} (ошибка запроса).")

    print(f"[Crypto Итог] Всего добавлено {total_added} исторических записей.")


def delete_all_crypto_prices():
    try:
        with transaction.atomic():
            deleted_count, _ = CryptoPrice.objects.all().delete()
        print(f"[!] УСПЕШНО УДАЛЕНО {deleted_count} записей из CryptoPrice.")
        return deleted_count
    except Exception as e:
        print(f"[-] КРИТИЧЕСКАЯ ОШИБКА при удалении всех записей CryptoPrice: {e}")
        return None

def fetch_from_cbrf(date):
    """
    Получает курсы валют от ЦБ РФ на указанную дату (datetime.date).
    Возвращает словарь {currency_code: rate}, где rate - курс за 1 единицу валюты к RUB.
    """
    date_str = date.strftime('%d/%m/%Y')
    url = f"http://www.cbr.ru/scripts/XML_daily.asp?date_req={date_str}"
    rates = {}
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding if response.apparent_encoding else 'windows-1251'
        root = ET.fromstring(response.text)

        target_cbrf_ids = {v['cbrf_id']: k for k, v in SELECTED_ASSETS.items()}

        for valute in root.findall('Valute'):
            cbrf_id = valute.get('ID')
            asset_pair = target_cbrf_ids.get(cbrf_id)
            if asset_pair:
                char_code = valute.find('CharCode').text
                if char_code == asset_pair.split('/')[0]:
                    value_str = valute.find('Value').text.replace(',', '.')
                    nominal_str = valute.find('Nominal').text
                    try:
                        value = Decimal(value_str)
                        nominal = Decimal(nominal_str)
                        if nominal == 0: continue
                        rate = value / nominal
                        rates[char_code] = rate
                    except (InvalidOperation, DivisionByZero, TypeError) as e:
                        print(f"[-] [CBRF] Ошибка расчета курса для {char_code} на {date_str}: {e}")
                else:
                    print(
                        f"[!] [CBRF] Несовпадение CharCode '{char_code}' и ожидаемого '{asset_pair.split('/')[0]}' для ID {cbrf_id}")

    except requests.exceptions.RequestException as e:
        print(f"[-] Ошибка сети при запросе к CBRF на дату {date_str}: {e}")
        return None
    except ET.ParseError as e:
        print(f"[-] Ошибка парсинга XML от CBRF на дату {date_str}: {e}")
        print(f"[-] [CBRF] Ответ сервера (начало): {response.text[:500]}...")
        return None
    except Exception as e:
        print(f"[-] Неожиданная ошибка при обработке данных CBRF на дату {date_str}: {e}")
        return None

    return rates

def fetch_frankfurter_for_range(start_date, end_date, base_currency='USD', target_currencies=None):
    """
    Получает курсы валют с frankfurter.app за ВЕСЬ ДИАПАЗОН дат одним запросом.
    Возвращает словарь словарей: { 'YYYY-MM-DD': {'CUR': Decimal(...), ...}, ... }
    """
    if target_currencies is None:
        target_currencies = []
    if not target_currencies:
        return {}

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    targets_str = ",".join([curr for curr in target_currencies if curr != base_currency])

    if not targets_str:
        if base_currency in target_currencies:
            rates_by_date = {}
            current_date = start_date
            while current_date <= end_date:
                rates_by_date[current_date.strftime('%Y-%m-%d')] = {base_currency: Decimal(1)}
                current_date += datetime.timedelta(days=1)
            return rates_by_date
        return {}

    url = f"https://api.frankfurter.app/{start_str}..{end_str}?from={base_currency}&to={targets_str}"
    print(f"[*] [Assets] Запрос Frankfurter (USD -> {targets_str}) за период {start_str} - {end_str}")

    try:
        response = requests.get(url, timeout=20)  # Увеличим таймаут для больших диапазонов
        response.raise_for_status()
        data = response.json()
        api_rates_by_date = data.get('rates', {})

        # Приводим все значения к Decimal
        processed_rates = {}
        for date_str, rates in api_rates_by_date.items():
            processed_rates[date_str] = {
                currency: Decimal(str(rate_val))
                for currency, rate_val in rates.items()
            }
            if base_currency in target_currencies:
                processed_rates[date_str][base_currency] = Decimal(1)

        return processed_rates

    except requests.exceptions.RequestException as e:
        print(f"[-] Ошибка сети при запросе к Frankfurter за диапазон: {e}")
        return None
    except Exception as e:
        print(f"[-] Неожиданная ошибка при обработке данных Frankfurter за диапазон: {e}")
        return None


def fetch_historical_asset_prices(start_date, end_date, assets=None, source_rub=DEFAULT_ASSET_SOURCE,
                                  source_usd=DEFAULT_USD_RATE_SOURCE):
    """
    Получает исторические цены для активов (валют) за диапазон дат.
    Оптимизировано для минимизации API-запросов и использования bulk_create.
    """
    if assets is None:
        assets = list(SELECTED_ASSETS.keys())

    start_loop_date = start_date.date() if isinstance(start_date, datetime.datetime) else start_date
    end_loop_date = end_date.date() if isinstance(end_date, datetime.datetime) else end_date

    target_base_currencies = {pair.split('/')[0] for pair in assets}
    start_dt_utc = make_aware(datetime.datetime.combine(start_loop_date, datetime.time.min),
                              timezone=datetime.timezone.utc)
    end_dt_utc = make_aware(datetime.datetime.combine(end_loop_date + datetime.timedelta(days=1), datetime.time.min),
                            timezone=datetime.timezone.utc)

    deleted_count, _ = AssetPrice.objects.filter(
        name_usd__in=list(target_base_currencies),
        name_rub='RUB',
        timestamp__gte=start_dt_utc,
        timestamp__lt=end_dt_utc
    ).delete()
    print(
        f"[Assets] Удалено {deleted_count} старых записей активов ({', '.join(assets)}) для диапазона {start_loop_date} - {end_loop_date}")

    # ---- ЭТАП 1: СБОР ВСЕХ ДАННЫХ В ПАМЯТЬ ----

    # 1.1 Получаем все данные от Frankfurter одним запросом
    all_frankfurter_data = {}
    if source_usd == 'frankfurter':
        frankfurter_targets = list(target_base_currencies)
        if 'RUB' not in frankfurter_targets:
            frankfurter_targets.append('RUB')

        all_frankfurter_data = fetch_frankfurter_for_range(
            start_loop_date, end_loop_date, 'USD', frankfurter_targets
        )
        if all_frankfurter_data is None:
            print("[!] [Assets] Не удалось получить данные от Frankfurter. Расчет курсов к USD будет невозможен.")
            all_frankfurter_data = {}

    # 1.2 Получаем данные от ЦБ РФ (в цикле, т.к. API не позволяет иначе)
    all_cbrf_data = {}
    if source_rub == 'cbrf':
        print(f"[*] [Assets] Запрос данных от CBRF за период {start_loop_date} - {end_loop_date}...")
        current_date_cbrf = start_loop_date
        while current_date_cbrf <= end_loop_date:
            rates = fetch_from_cbrf(current_date_cbrf)
            if rates:
                all_cbrf_data[current_date_cbrf.strftime('%Y-%m-%d')] = rates
            time.sleep(0.1)
            current_date_cbrf += datetime.timedelta(days=1)
        print("[*] [Assets] Сбор данных от CBRF завершен.")

    # ---- ЭТАП 2: ОБРАБОТКА ДАННЫХ И ПОДГОТОВКА К ЗАПИСИ В БД ----
    objects_to_create = []
    unique_keys = set()  # Для дополнительной защиты от дублей перед bulk_create

    current_date = start_loop_date
    while current_date <= end_loop_date:
        date_str = current_date.strftime('%Y-%m-%d')
        record_timestamp = make_aware(datetime.datetime.combine(current_date, datetime.time(12, 0)),
                                      timezone=datetime.timezone.utc)

        cbrf_rates_today = all_cbrf_data.get(date_str, {})
        frankfurter_rates_today = all_frankfurter_data.get(date_str, {})

        for asset_pair in assets:
            base_currency, quote_currency = asset_pair.split('/')
            if quote_currency != 'RUB':
                continue

            key = (base_currency, record_timestamp.date())
            if key in unique_keys:
                continue

            price_rub = cbrf_rates_today.get(base_currency)

            price_usd = None
            if base_currency == 'USD':
                price_usd = Decimal(1)
            elif base_currency in frankfurter_rates_today:
                rate_usd_to_base = frankfurter_rates_today.get(base_currency)
                try:
                    if rate_usd_to_base and rate_usd_to_base != 0:
                        price_usd = Decimal(1) / rate_usd_to_base
                except (DivisionByZero, InvalidOperation):
                    pass

            if price_rub is not None or price_usd is not None:
                objects_to_create.append(
                    AssetPrice(
                        name_usd=base_currency,
                        name_rub='RUB',
                        timestamp=record_timestamp,
                        price_rub=price_rub,
                        price_usd=price_usd
                    )
                )
                unique_keys.add(key)

        current_date += datetime.timedelta(days=1)

    # ---- ЭТАП 3: ЗАПИСЬ В БАЗУ ДАННЫХ ОДНИМ ЗАПРОСОМ ----
    if objects_to_create:
        try:
            objects_to_create.sort(key=lambda x: x.timestamp)
            created_objects = AssetPrice.objects.bulk_create(objects_to_create, ignore_conflicts=True)
            print(
                f"[+] [Assets] Добавлено {len(created_objects)} новых записей активов (всего подготовлено {len(objects_to_create)})")
        except Exception as e:
            print(f"[-] [Assets] Критическая ошибка при массовой вставке (bulk_create): {e}")
    else:
        print("[*] [Assets] Нет новых данных для добавления в базу.")

    print("[Assets Итог] Обработка валютных пар завершена.")


def delete_all_asset_prices():
    """
    Удаляет ВСЕ записи из модели AssetPrice.
    """
    try:
        with transaction.atomic():
            deleted_count, _ = AssetPrice.objects.all().delete()
        print(f"[!] УСПЕШНО УДАЛЕНО {deleted_count} записей из AssetPrice.")
        return deleted_count
    except Exception as e:
        print(f"[-] КРИТИЧЕСКАЯ ОШИБКА при удалении всех записей AssetPrice: {e}")
        return None

def fetch_from_yfinance(ticker, start_date, end_date):
    """
    Получает исторические данные (дневные свечи) с Yahoo Finance.
    Возвращает список кортежей: [(timestamp, close_price, volume), ...].
    """
    print(f"[*] [Stocks] Запрос данных для '{ticker}' с Yahoo Finance...")
    try:
        stock = yf.Ticker(ticker)
        end_date_yf = (end_date.date() if isinstance(end_date, datetime.datetime) else end_date) + datetime.timedelta(
            days=1)

        hist = stock.history(start=start_date, end=end_date_yf, interval="1d")

        if hist.empty:
            print(f"[!] [Stocks] Yahoo Finance не вернул данных для '{ticker}' за указанный период.")
            return []

        processed_data = []
        for index_date, row in hist.iterrows():
            if is_aware(index_date):
                timestamp = index_date.astimezone(datetime.timezone.utc)
            else:
                timestamp = make_aware(index_date, timezone=datetime.timezone.utc)

            timestamp = timestamp.replace(hour=12, minute=0, second=0, microsecond=0)

            if 'Close' not in row or 'Volume' not in row:
                continue

            try:
                close_price = Decimal(str(row['Close']))
                volume = int(row['Volume'])
                processed_data.append((timestamp, close_price, volume))
            except (InvalidOperation, TypeError, ValueError) as e:
                print(f"[-] [Stocks] Ошибка обработки строки для {ticker} на {index_date}: {e}")

        return processed_data

    except Exception as e:
        print(f"[-] [Stocks] КРИТИЧЕСКАЯ ОШИБКА при запросе к yfinance для '{ticker}': {e}")
        return None

def fetch_from_moex(ticker, start_date, end_date):
    """
    Получает исторические данные с Moscow Exchange (MOEX) ISS API.
    API имеет ограничение в 100 записей за раз, поэтому реализована пагинация.
    """
    print(f"[*] [Stocks] Запрос данных для '{ticker}' с MOEX...")

    api_url = f"https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"

    all_rows = []
    start_index = 0

    # MOEX API отдает данные страницами по 100 штук
    while True:
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'till': end_date.strftime('%Y-%m-%d'),
            'start': start_index,
            'limit': 100,
            'iss.meta': 'off',
            'lang': 'ru',
        }

        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()  # Проверка на ошибки HTTP (4xx, 5xx)
            data = response.json()

            history_data = data.get('history', {})
            rows = history_data.get('data', [])

            if not rows:
                break

            all_rows.extend(rows)
            start_index += len(rows)
            time.sleep(0.5)  # Пауза, чтобы не нагружать API

        except requests.exceptions.RequestException as e:
            print(f"[-] [Stocks] Ошибка сети при запросе к MOEX для '{ticker}': {e}")
            return None
        except Exception as e:
            print(f"[-] [Stocks] КРИТИЧЕСКАЯ ОШИБКА при работе с MOEX для '{ticker}': {e}")
            return None

    if not all_rows:
        print(f"[!] [Stocks] MOEX не вернул данных для '{ticker}' за указанный период.")
        return []

    try:
        columns = data['history']['columns']
        date_idx = columns.index('TRADEDATE')
        close_idx = columns.index('CLOSE')
        volume_idx = columns.index('VOLUME')
    except (KeyError, ValueError):
        print(f"[-] [Stocks] Неожиданная структура ответа от MOEX для '{ticker}'.")
        return None

    processed_data = []
    for row in all_rows:
        try:
            trade_date = datetime.datetime.strptime(row[date_idx], '%Y-%m-%d').date()
            timestamp = make_aware(
                datetime.datetime.combine(trade_date, datetime.time(12, 0)),
                timezone=timezone.utc
            )
            close_price = Decimal(str(row[close_idx]))
            volume = int(row[volume_idx])
            processed_data.append((timestamp, close_price, volume))
        except (ValueError, TypeError, InvalidOperation) as e:
            print(f"[-] [Stocks] Ошибка обработки строки MOEX для {ticker} на {row[date_idx]}: {e}")

    return processed_data


def fetch_historical_stock_prices(start_date, end_date, stocks=None):
    """
    Основная функция для получения и сохранения исторических цен на акции.
    Теперь умеет работать с разными источниками данных (yfinance, moex).
    """
    if stocks is None:
        stocks_to_process = SELECTED_STOCKS
    else:
        stocks_to_process = {name: data for name, data in SELECTED_STOCKS.items() if name in stocks}

    if not stocks_to_process:
        print("[!] [Stocks] Нет выбранных акций для обработки.")
        return

    start_dt_utc = make_aware(datetime.datetime.combine(start_date, datetime.time.min), timezone=timezone.utc)
    end_dt_utc = make_aware(datetime.datetime.combine(end_date, datetime.time.max), timezone=timezone.utc)

    tickers_to_delete = [v['ticker'] for v in stocks_to_process.values()]
    deleted_count, _ = StockPrice.objects.filter(
        ticker__in=tickers_to_delete,
        timestamp__gte=start_dt_utc,
        timestamp__lte=end_dt_utc
    ).delete()
    print(
        f"[Stocks] Удалено {deleted_count} старых записей акций ({', '.join(tickers_to_delete)}) для диапазона {start_date} - {end_date}")

    total_added = 0
    for stock_name, stock_info in stocks_to_process.items():
        ticker = stock_info['ticker']
        currency = stock_info['currency']
        source = stock_info.get('source', 'yfinance')

        price_data = None

        if source == 'moex':
            price_data = fetch_from_moex(ticker, start_date, end_date)
        elif source == 'yfinance':
            price_data = fetch_from_yfinance(ticker, start_date, end_date)
        else:
            print(f"[!] [Stocks] Неизвестный источник данных '{source}' для акции '{stock_name}'. Пропускаем.")
            continue

        if price_data:
            objects_to_create = []
            for ts, close, vol in price_data:
                stock_price_obj = StockPrice(
                    ticker=ticker,
                    timestamp=ts,
                    close_price=close,
                    volume=vol
                )
                if currency == 'USD':
                    stock_price_obj.price_usd = close
                elif currency == 'RUB':
                    stock_price_obj.price_rub = close

                objects_to_create.append(stock_price_obj)

            if objects_to_create:
                try:
                    created_objects = StockPrice.objects.bulk_create(objects_to_create, ignore_conflicts=True)
                    num_created = len(created_objects)
                    print(f"[+] [Stocks] Добавлено {num_created} записей для {stock_name} ({ticker})")
                    total_added += num_created
                except Exception as e:
                    print(f"[-] [Stocks] Ошибка bulk_create для {ticker}: {e}")

    print(f"[Stocks Итог] Всего добавлено {total_added} записей о ценах на акции.")


def delete_all_stock_prices():
    """
    Удаляет ВСЕ записи из модели StockPrice.
    """
    try:
        with transaction.atomic():
            deleted_count, _ = StockPrice.objects.all().delete()
        print(f"[!] УСПЕШНО УДАЛЕНО {deleted_count} записей из StockPrice.")
        return deleted_count
    except Exception as e:
        print(f"[-] КРИТИЧЕСКАЯ ОШИБКА при удалении всех записей StockPrice: {e}")
        return None