import datetime
import os

import logging
import json
import traceback
import threading

from pathlib import Path

import numpy as np

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.timezone import timedelta
from django.db.models import Avg

from src.modules.assets_analysis.models import CryptoPrice, AssetPrice, StockPrice, NewsArticle

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    import joblib
    
    import tensorflow as tf

    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional, Input
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.optimizers import Adam

    from sklearn.preprocessing import StandardScaler

    TF_IMPORTED = True
except ImportError as e:
    TF_IMPORTED = False
    IMPORT_ERROR_MSG = str(e)

logger = logging.getLogger(__name__)

keras_lock = threading.Lock()

# Параметры
DEFAULT_SEQUENCE_LENGTH = 60
DEFAULT_EPOCHS = 150
DEFAULT_BATCH_SIZE = 32
VALIDATION_SPLIT_RATIO = 0.15
EARLY_STOPPING_PATIENCE = 15
MIN_VAL_POINTS_ABSOLUTE = DEFAULT_SEQUENCE_LENGTH + 10
DEFAULT_USE_SENTIMENT = False
DEFAULT_SENTIMENT_WINDOW_DAYS = 7
DEFAULT_SENTIMENT_IMPACT_FACTOR = 0.03
MODEL_SAVE_DIR = Path("trained_models")


class Command(BaseCommand):
    help = ('Обучает LSTM модель и предсказывает будущие цены криптовалют, валютных пар или акций.')

    def add_arguments(self, parser):
        parser.add_argument('--coin', type=str, required=False, help='Внутреннее имя монеты (например, bitcoin)')
        parser.add_argument('--asset-pair', type=str, required=False,
                            help='Валютная пара для предсказания (например, USD/RUB)')
        parser.add_argument('--ticker', type=str, required=False, help='Тикер акции (например, TSLA)')
        parser.add_argument('--train-days', type=int, required=True)
        parser.add_argument('--predict-days', type=int, required=True)
        parser.add_argument('--predict-until', type=str, default=None)
        parser.add_argument('--sequence-length', type=int, default=DEFAULT_SEQUENCE_LENGTH)
        parser.add_argument('--epochs', type=int, default=DEFAULT_EPOCHS)
        parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE)
        parser.add_argument('--patience', type=int, default=EARLY_STOPPING_PATIENCE)
        parser.add_argument('--force-retrain', action='store_true')
        parser.add_argument('--use-sentiment', action='store_true', default=DEFAULT_USE_SENTIMENT)
        parser.add_argument('--sentiment-window', type=int, default=DEFAULT_SENTIMENT_WINDOW_DAYS)
        parser.add_argument('--sentiment-factor', type=float, default=DEFAULT_SENTIMENT_IMPACT_FACTOR)

    def _calculate_percentage_change(self, prices):
        prices_arr = np.array(prices, dtype=float)
        if len(prices_arr) < 2: return np.array([])
        diff, denominators = np.diff(prices_arr), prices_arr[:-1]
        pct_changes = np.zeros_like(denominators, dtype=float)
        safe_mask = np.abs(denominators) > 1e-9
        pct_changes[safe_mask] = diff[safe_mask] / denominators[safe_mask]
        return pct_changes

    def _handle_split_and_validation(self, data, sequence_length, val_split_ratio, min_val_points_in_set):
        total_points, min_train_seq = len(data), sequence_length + 1
        min_total_for_split = min_train_seq + min_val_points_in_set
        if total_points < min_total_for_split:
            self.stdout.write(
                self.style.WARNING(f"[-] Недостаточно данных ({total_points}) для валидации. Обучение без валидации."))
            return data, None, False
        val_size = max(int(total_points * val_split_ratio), min_val_points_in_set)
        if val_size >= total_points - min_train_seq:
            self.stdout.write(self.style.WARNING(
                f"[-] Расчетный размер валидации ({val_size}) не оставляет данных для обучения. Обучение без валидации."))
            return data, None, False
        split_idx = total_points - val_size
        train_data, val_data = data[:split_idx], data[split_idx:]
        if len(train_data) < min_train_seq:
            self.stdout.write(self.style.WARNING(
                f"[-] Даже после корректировки разделения, недостаточно данных для обучающей последовательности. Обучение без валидации."))
            return data, None, False
        self.stdout.write(f"[*] Разделение данных: Обучение={len(train_data)}, Валидация={len(val_data)}")
        return train_data, val_data, True

    def _create_sequences(self, input_data, seq_length):
        X, y = [], []
        if input_data is None or len(input_data) <= seq_length: return np.array(X), np.array(y)
        for i in range(seq_length, len(input_data)):
            X.append(input_data[i - seq_length:i, 0])
            y.append(input_data[i, 0])
        return np.array(X), np.array(y)

    def _get_average_sentiment(self, coin_name, target_date, window_days):
        if window_days <= 0: return 0.0
        start_date, end_date = target_date - timedelta(days=window_days - 1), target_date
        news_qs = NewsArticle.objects.filter(published_at__date__gte=start_date, published_at__date__lte=end_date,
                                             relevant_coins__contains=coin_name, sentiment_score__isnull=False)
        avg_sentiment = news_qs.aggregate(avg_score=Avg('sentiment_score'))['avg_score']
        return avg_sentiment if avg_sentiment is not None else 0.0

    def handle(self, *args, **options):
        if not TF_IMPORTED:
            self.stderr.write(self.style.ERROR(f"[-] Критическая ошибка импорта: {IMPORT_ERROR_MSG}."));
            self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END");
            return

        ### Получаем ticker и проверяем, что указан только один тип актива ###
        coin_name = options.get('coin')
        asset_pair = options.get('asset_pair')
        ticker = options.get('ticker')

        num_targets = sum([bool(coin_name), bool(asset_pair), bool(ticker)])
        if num_targets == 0:
            raise CommandError("Необходимо указать один из аргументов: --coin, --asset-pair или --ticker.")
        if num_targets > 1:
            raise CommandError("Можно указать только один из аргументов: --coin, --asset-pair или --ticker.")
        if coin_name:
            target_type, target_name, target_model, price_field = 'crypto', coin_name, CryptoPrice, 'price_usd'
            model_file_prefix, filter_kwargs_base = target_name, {'name': target_name}
        elif asset_pair:
            target_type, target_name, target_model, price_field = 'asset', asset_pair, AssetPrice, 'price_rub'
            model_file_prefix = target_name.replace('/', '_')
            try:
                name_usd, name_rub = target_name.split('/');
                filter_kwargs_base = {'name_usd': name_usd,
                                      'name_rub': name_rub}
            except ValueError:
                raise CommandError(f"Неверный формат --asset-pair: '{target_name}'. Ожидается 'USD/RUB'.")
        elif ticker:
            target_name = ticker
            target_type = 'stock'
            target_model = StockPrice
            model_file_prefix = target_name.replace('.', '_')
            filter_kwargs_base = {'ticker': target_name}
            RUB_TICKERS = ['LKOH']

            if target_name.upper() in RUB_TICKERS:
                price_field = 'price_rub'
                self.stdout.write(self.style.SUCCESS(
                    f"[*] Обнаружен российский тикер '{target_name}'. Используется поле 'price_rub'."))
            else:
                # Для всех остальных акций по умолчанию используется 'price_usd'
                price_field = 'price_usd'
                self.stdout.write(self.style.SUCCESS(
                    f"[*] Тикер '{target_name}' не в списке российских. Используется поле 'price_usd' по умолчанию."))

        train_days, predict_days, predict_until_str = options['train_days'], options['predict_days'], options[
            'predict_until']
        sequence_length, max_epochs, batch_size, patience, force_retrain = options['sequence_length'], options[
            'epochs'], options['batch_size'], options['patience'], options['force_retrain']
        use_sentiment, sentiment_window, sentiment_factor = options['use_sentiment'], options['sentiment_window'], \
            options['sentiment_factor']

        self.stdout.write(f"[*] Запуск предсказания для {target_type.upper()}: {target_name} на {predict_days} дней...")

        ### Отключаем sentiment для акций, т.к. модель новостей не адаптирована ###
        if target_type in ['asset', 'stock'] and use_sentiment:
            self.stdout.write(self.style.WARNING(
                f"[!] Корректировка по Sentiment не поддерживается для типа '{target_type}' и будет отключена."))
            use_sentiment = False

        predict_end_date = None
        if predict_until_str:
            try:
                parsed_date = datetime.datetime.strptime(predict_until_str, '%Y-%m-%d').date()
                predict_end_date = timezone.make_aware(datetime.datetime.combine(parsed_date, datetime.time.max),
                                                       datetime.timezone.utc)
            except ValueError:
                self.stderr.write(self.style.WARNING(
                    f"[-] Неверный формат даты для --predict-until. Используется последняя дата из БД."))

        if predict_end_date is None:
            try:
                latest_entry = target_model.objects.filter(**filter_kwargs_base).only('timestamp').latest('timestamp')
                predict_end_date = latest_entry.timestamp
            except target_model.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"[-] Не найдено записей в БД для {target_name}."));
                self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END");
                return

        MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        model_filename = f"{model_file_prefix}_lstm_pct_change_seq{sequence_length}.keras"
        scaler_filename = f"{model_file_prefix}_scaler_pct_change_seq{sequence_length}.joblib"
        model_path, scaler_path = MODEL_SAVE_DIR / model_filename, MODEL_SAVE_DIR / scaler_filename

        model, scaler = None, None
        if not force_retrain and model_path.exists() and scaler_path.exists():
            try:
                with keras_lock:
                    self.stdout.write(f"[*] [{target_name}] Попытка загрузки модели в критической секции...")
                    model = load_model(model_path)
                scaler = joblib.load(scaler_path)
                if model.input_shape[1] != sequence_length: model, scaler = None, None
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"[-] Не удалось загрузить модель/скейлер LSTM: {e}."));
                model, scaler = None, None

        if model is None or scaler is None:
            try:
                filter_kwargs_train = {**filter_kwargs_base,
                                       'timestamp__gte': predict_end_date - timedelta(days=train_days),
                                       'timestamp__lt': predict_end_date}
                prices_qs = target_model.objects.filter(**filter_kwargs_train).order_by('timestamp').values_list(
                    price_field, 'timestamp')
                prices_data_list = list(prices_qs)
                min_required_prices = sequence_length + 2 + MIN_VAL_POINTS_ABSOLUTE
                if len(prices_data_list) < min_required_prices:
                    self.stderr.write(self.style.ERROR(
                        f"[-] Недостаточно данных для обучения ({len(prices_data_list)} точек, требуется {min_required_prices})."));
                    self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END");
                    return

                all_training_data_for_lstm = self._calculate_percentage_change(
                    np.array([item[0] for item in prices_data_list], dtype=float)).reshape(-1, 1)
                train_data_pct, val_data_pct, use_validation = self._handle_split_and_validation(
                    all_training_data_for_lstm, sequence_length, VALIDATION_SPLIT_RATIO, MIN_VAL_POINTS_ABSOLUTE)
                scaler = StandardScaler()
                scaled_train_data_pct = scaler.fit_transform(train_data_pct)
                X_train, y_train = self._create_sequences(scaled_train_data_pct, sequence_length)
                if len(X_train) == 0: self.stderr.write(
                    self.style.ERROR(f"[-] Не удалось создать обучающие последовательности LSTM.")); self.stdout.write(
                    "PREDICTION_START\n[]\nPREDICTION_END"); return
                X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
                X_val, y_val = None, None
                if use_validation:
                    scaled_val_data_pct = scaler.transform(val_data_pct)
                    X_val, y_val = self._create_sequences(scaled_val_data_pct, sequence_length)
                    if len(X_val) > 0:
                        X_val = np.reshape(X_val, (X_val.shape[0], X_val.shape[1], 1))
                    else:
                        use_validation = False

                with keras_lock:
                    self.stdout.write(
                        f"[*] [{target_name}] Вход в критическую секцию Keras для создания и обучения модели...")
                    tf.keras.backend.clear_session()
                    model = Sequential([
                        Input(shape=(sequence_length, 1)),
                        Bidirectional(LSTM(units=100, return_sequences=True)),
                        Dropout(0.3),
                        Bidirectional(LSTM(units=50, return_sequences=False)),
                        Dropout(0.3),
                        Dense(units=25, activation='relu'),
                        Dense(units=1)
                    ])
                    model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
                    self.stdout.write(f"[*] [{target_name}] Модель скомпилирована.")

                    callbacks = []
                    fit_kwargs = {'epochs': max_epochs, 'batch_size': batch_size, 'verbose': 0, 'shuffle': False}
                    if use_validation and X_val is not None:
                        callbacks.append(
                            EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True, verbose=1))
                        fit_kwargs['validation_data'] = (X_val, y_val)
                    else:
                        callbacks.append(
                            EarlyStopping(monitor='loss', patience=patience, restore_best_weights=True, verbose=1))

                    history = model.fit(X_train, y_train, **fit_kwargs, callbacks=callbacks)
                    self.stdout.write(self.style.SUCCESS(
                        f"[*] [{target_name}] Обучение LSTM завершено за {len(history.history['loss'])} эпох. Выход из секции."))

                model.save(model_path)
                joblib.dump(scaler, scaler_path)
                self.stdout.write(self.style.SUCCESS(f"[*] Модель для {target_name} успешно обучена и сохранена."))

            except Exception as e:
                logger.exception(f"Ошибка ОБУЧЕНИЯ для {target_name}")
                self.stderr.write(
                    self.style.ERROR(f"[-] Ошибка ОБУЧЕНИЯ: {type(e).__name__}: {e}\n{traceback.format_exc()}"))
                self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END");
                return

        if model is None or scaler is None:
            self.stderr.write(self.style.ERROR(f"[-] Предсказание невозможно: Модель или Скейлер отсутствуют."));
            self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END");
            return

        try:
            filter_kwargs_predict = {**filter_kwargs_base, 'timestamp__lt': predict_end_date}
            latest_prices_data_qs = target_model.objects.filter(**filter_kwargs_predict).order_by(
                '-timestamp').values_list(price_field, 'timestamp')[:sequence_length + 1]

            if len(latest_prices_data_qs) < sequence_length + 1:
                self.stderr.write(self.style.ERROR(
                    f"[-] Недостаточно данных ({len(latest_prices_data_qs)}) для инициализации прогноза."));
                self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END");
                return

            initial_prices_abs = np.array([item[0] for item in latest_prices_data_qs], dtype=float)[::-1]
            last_sequence_pct_changes = self._calculate_percentage_change(initial_prices_abs)
            last_actual_abs_price = initial_prices_abs[-1]
            last_actual_date_used = list(latest_prices_data_qs)[0][1].date()
            last_sequence_scaled = scaler.transform(last_sequence_pct_changes.reshape(-1, 1))
            current_batch = last_sequence_scaled.reshape((1, sequence_length, 1))
            future_predictions_scaled_pct_changes = []

            with keras_lock:
                self.stdout.write(f"[*] [{target_name}] Вход в критическую секцию для предсказания...")
                for i in range(predict_days):
                    next_pred_scaled_pct = model.predict(current_batch, verbose=0)[0]
                    future_predictions_scaled_pct_changes.append(next_pred_scaled_pct)
                    current_batch = np.append(current_batch[:, 1:, :], next_pred_scaled_pct.reshape((1, 1, 1)), axis=1)
                self.stdout.write(f"[*] [{target_name}] Предсказание завершено. Выход из секции.")

            predicted_pct_changes_lstm = scaler.inverse_transform(
                np.array(future_predictions_scaled_pct_changes).reshape(-1, 1))

            predictions_output, current_reconstructed_price = [], last_actual_abs_price
            for i in range(predict_days):
                predict_date = last_actual_date_used + timedelta(days=i + 1)
                final_price_value = float(current_reconstructed_price) * (1 + predicted_pct_changes_lstm[i, 0])
                if use_sentiment:  # Эта ветка не будет выполняться для акций из-за проверки выше
                    sentiment_score = self._get_average_sentiment(target_name, predict_date, sentiment_window)
                    adjustment = sentiment_score * sentiment_factor * final_price_value
                    final_price_value += adjustment
                final_price_value = max(0.0, final_price_value)

                predictions_output.append({"date": predict_date.isoformat(), "price": float(final_price_value)})
                current_reconstructed_price = final_price_value

            self.stdout.write("PREDICTION_START\n" + json.dumps(predictions_output, indent=None,
                                                                separators=(',', ':')) + "\nPREDICTION_END")
            self.stdout.write(self.style.SUCCESS(f"[*] Предсказание для {target_name} успешно завершено."))

        except Exception as e:
            logger.exception(f"Ошибка ПРЕДСКАЗАНИЯ для {target_name}")
            self.stderr.write(
                self.style.ERROR(f"[-] Ошибка ПРЕДСКАЗАНИЯ: {type(e).__name__}: {e}\n{traceback.format_exc()}"))
            self.stdout.write("PREDICTION_START\n[]\nPREDICTION_END")