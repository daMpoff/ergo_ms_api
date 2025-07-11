from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, pagination

import os
from io import StringIO

import json
import re
import logging
import shutil

from datetime import date

from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.conf import settings

from src.modules.assets_analysis.models import (
    CryptoPrice, 
    NewsArticle, 
    AssetPrice, 
    StockPrice
)
from src.modules.assets_analysis.scripts import (
    delete_all_crypto_prices,
    delete_all_asset_prices,
    delete_all_stock_prices
)
from src.modules.assets_analysis.serializers import (
    CryptoPriceSerializer, 
    NewsArticleSerializer, 
    AssetPriceSerializer, 
    StockPriceSerializer
)

logger = logging.getLogger(__name__)

# Функция для удаления всех записей NewsArticle
def _internal_delete_all_news_articles():
    """Удаляет все записи из модели NewsArticle."""
    try:
        count, _ = NewsArticle.objects.all().delete()
        logger.info(f"Успешно удалено {count} записей NewsArticle.")
        return count
    except Exception as e:
        logger.error(f"Ошибка при удалении записей NewsArticle: {e}", exc_info=True)
        return None

class StandardResultsSetPagination(pagination.PageNumberPagination):
    """ Стандартная пагинация для списков. """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# --- Класс CryptoPriceListAPIView ---
class CryptoPriceListAPIView(generics.ListAPIView):
    """
    API для получения списка цен криптовалют.
    """
    queryset = CryptoPrice.objects.all().order_by('-timestamp')
    serializer_class = CryptoPriceSerializer
    # pagination_class = StandardResultsSetPagination


# --- Класс AssetPriceListAPIView  ---
class AssetPriceListAPIView(generics.ListAPIView):
    """
    API для получения списка цен активов (валют).
    """
    queryset = AssetPrice.objects.all().order_by('-timestamp')
    serializer_class = AssetPriceSerializer
    # pagination_class = StandardResultsSetPagination


# --- Класс StockPriceListAPIView ---
class StockPriceListAPIView(generics.ListAPIView):
    """
    API для получения списка цен на акции.
    """
    queryset = StockPrice.objects.all().order_by('-timestamp')
    serializer_class = StockPriceSerializer
    # pagination_class = StandardResultsSetPagination


# --- Класс NewsArticleListAPIView ---
class NewsArticleListAPIView(generics.ListAPIView):
    """
    API для получения списка новостных статей с фильтрацией и пагинацией.
    """
    serializer_class = NewsArticleSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """ Фильтрация новостей по параметрам запроса. """
        queryset = NewsArticle.objects.all().order_by('-published_at')

        start_date_str = self.request.query_params.get('startDate', None)
        end_date_str = self.request.query_params.get('endDate', None)
        coins_str = self.request.query_params.get('coins', None)
        sentiment = self.request.query_params.get('sentiment', None)

        if start_date_str:
            start_dt_parsed = parse_date(start_date_str)
            if start_dt_parsed:
                queryset = queryset.filter(published_at__date__gte=start_dt_parsed)
        if end_date_str:
            end_dt_parsed = parse_date(end_date_str)
            if end_dt_parsed:
                queryset = queryset.filter(published_at__date__lte=end_dt_parsed)

        if coins_str:
            coins_list = [coin.strip().lower() for coin in coins_str.split(',') if coin.strip()]
            if coins_list:
                coin_query = Q()
                for coin in coins_list:
                    coin_query |= Q(relevant_coins__contains=coin)
                queryset = queryset.filter(coin_query)

        if sentiment and sentiment in ['positive', 'negative', 'neutral']:
            queryset = queryset.filter(sentiment_label=sentiment)

        return queryset

# --- Класс ExecuteCommandAPIView ---
class ExecuteCommandAPIView(APIView):
    """
    API для запуска команд управления данными:
    - fetch_price: Обновление исторических данных (требует startDate, endDate и хотя бы один из: coins, assets, stocks).
    - fetch_news: Скачивание новостей (МОЖЕТ принимать startDate, endDate).
    - delete_all: Удаление ВСЕХ исторических данных (цены крипты, активов, акций, новости).
    - delete_models: Удаление всех сохраненных моделей прогнозов.
    """

    def post(self, request, *args, **kwargs):
        try:
            command = request.data.get('command')

            if not command:
                if all(k in request.data for k in ['startDate', 'endDate']):
                    logger.warning("[API] Команда не указана, попытка обработки как fetch_price (старый формат)")
                    command = 'fetch_price'
                else:
                    raise ValidationError('Параметр "command" обязателен.')

            if command == 'fetch_price':
                logger.info(f"[API] Обработка команды: {command}")
                today_str = date.today().strftime('%Y-%m-%d')
                start_date_str = request.data.get("startDate")
                end_date_str = request.data.get("endDate", today_str)
                coins = request.data.get("coins")
                assets = request.data.get("assets")
                stocks = request.data.get("stocks")

                if not start_date_str:
                    raise ValidationError('Параметр "startDate" обязателен для команды fetch_price.')
                # Проверяем, что хотя бы один тип актива указан
                if not coins and not assets and not stocks:
                    raise ValidationError(
                        'Необходимо указать хотя бы один из параметров: "coins", "assets" или "stocks" для команды fetch_price.')
                try:
                    start_dt_obj = parse_date(start_date_str)
                    end_dt_obj = parse_date(end_date_str)
                    if not start_dt_obj or not end_dt_obj:
                        raise ValueError("Неверный формат даты.")
                    if start_dt_obj > end_dt_obj:
                        raise ValidationError('Начальная дата не может быть позже конечной.')
                except (ValueError, TypeError):
                    raise ValidationError('Неверный формат даты или тип для fetch_price. Используйте YYYY-MM-DD.')

                # Добавляем валидацию для акций
                if coins and not isinstance(coins, list):
                    raise ValidationError('Параметр "coins" должен быть списком.')
                if assets and not isinstance(assets, list):
                    raise ValidationError('Параметр "assets" должен быть списком.')
                if stocks and not isinstance(stocks, list):
                    raise ValidationError('Параметр "stocks" должен быть списком.')

                out = StringIO()
                err = StringIO()
                command_args = ['fetch_price', '--start-date', start_date_str, '--end-date', end_date_str]

                if coins and len(coins) > 0:
                    command_args.append('--coins')
                    command_args.extend(coins)
                if assets and len(assets) > 0:
                    command_args.append('--assets')
                    command_args.extend(assets)
                if stocks and len(stocks) > 0:
                    command_args.append('--stocks')
                    command_args.extend(stocks)

                try:
                    logger.info(f"[*] Вызов команды fetch_price: {' '.join(command_args)}")
                    call_command(*command_args, stdout=out, stderr=err)
                    logger.info(f"[*] Команда fetch_price завершена.")
                except CommandError as cmd_e:
                    logger.error(f"Ошибка выполнения команды fetch_price: {cmd_e}. Stderr: {err.getvalue()}")
                    return Response({'status': 'error', 'message': f'Ошибка выполнения команды обновления цен: {cmd_e}',
                                     'details': err.getvalue()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                errors_val = err.getvalue()
                output_val = out.getvalue()
                if errors_val: logger.warning(f"Команда fetch_price завершилась с сообщениями в stderr:\n{errors_val}")
                logger.debug(f"Команда fetch_price stdout:\n{output_val}")

                return Response(
                    {'status': 'success', 'message': 'Команда обновления цен успешно запущена.', 'output': output_val,
                     'errors': errors_val if errors_val else None}, status=status.HTTP_200_OK)

            elif command == 'fetch_news':
                logger.info(f"[API] Обработка команды: {command}")
                start_date_str = request.data.get("startDate")
                end_date_str = request.data.get("endDate")
                out = StringIO()
                err = StringIO()
                command_args = ['fetch_news']
                if start_date_str:
                    if not end_date_str:
                        end_date_str = date.today().strftime('%Y-%m-%d')
                    logger.info(f"[API] Для fetch_news переданы даты: start={start_date_str}, end={end_date_str}")
                    try:
                        start_dt_obj = parse_date(start_date_str)
                        end_dt_obj = parse_date(end_date_str)
                        if not start_dt_obj or not end_dt_obj: raise ValueError("Неверный формат даты.")
                        if start_dt_obj > end_dt_obj: raise ValidationError(
                            'Начальная дата не может быть позже конечной для fetch_news.')
                    except (ValueError, TypeError):
                        raise ValidationError('Неверный формат даты для fetch_news. Используйте YYYY-MM-DD.')
                    command_args.extend(['--start-date', start_date_str, '--end-date', end_date_str])
                else:
                    logger.info(
                        "[API] Даты startDate/endDate не переданы для fetch_news, команда будет использовать логику по умолчанию (на основе --days).")
                try:
                    logger.info(f"[*] Вызов команды fetch_news: {' '.join(command_args)}")
                    call_command(*command_args, stdout=out, stderr=err)
                    logger.info(f"[*] Команда fetch_news завершена.")
                except CommandError as cmd_e:
                    logger.error(f"Ошибка выполнения команды fetch_news: {cmd_e}. Stderr: {err.getvalue()}")
                    return Response(
                        {'status': 'error', 'message': f'Ошибка выполнения команды обновления новостей: {cmd_e}',
                         'details': err.getvalue()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                errors_val = err.getvalue()
                output_val = out.getvalue()
                if errors_val: logger.warning(f"Команда fetch_news завершилась с сообщениями в stderr:\n{errors_val}")
                logger.debug(f"Команда fetch_news stdout:\n{output_val}")
                return Response({'status': 'success', 'message': 'Команда обновления новостей успешно запущена.',
                                 'output': output_val, 'errors': errors_val if errors_val else None},
                                status=status.HTTP_200_OK)

            elif command == 'delete_all':
                logger.info(f"[API] Обработка команды: {command} (удаление всех данных)")
                # Добавляем переменные для акций
                deleted_crypto_count, deleted_assets_count, deleted_stocks_count, deleted_news_count = None, None, None, None
                crypto_errors_occurred, assets_errors_occurred, stocks_errors_occurred, news_errors_occurred = False, False, False, False
                response_messages = []
                try:
                    deleted_crypto_count = delete_all_crypto_prices()
                    if deleted_crypto_count is not None:
                        response_messages.append(f'{deleted_crypto_count} записей цен криптовалют успешно удалены.')
                    else:
                        crypto_errors_occurred = True; response_messages.append(
                        'Ошибка при удалении данных цен криптовалют (функция вернула None).')
                except Exception as e:
                    crypto_errors_occurred = True; response_messages.append(
                    f'Внутренняя ошибка при удалении цен криптовалют: {e}')
                try:
                    deleted_assets_count = delete_all_asset_prices()
                    if deleted_assets_count is not None:
                        response_messages.append(f'{deleted_assets_count} записей цен активов успешно удалены.')
                    else:
                        assets_errors_occurred = True; response_messages.append(
                        'Ошибка при удалении данных цен активов (функция вернула None).')
                except Exception as e:
                    assets_errors_occurred = True; response_messages.append(
                    f'Внутренняя ошибка при удалении цен активов: {e}')
                # Добавляем блок удаления акций
                try:
                    deleted_stocks_count = delete_all_stock_prices()
                    if deleted_stocks_count is not None:
                        response_messages.append(f'{deleted_stocks_count} записей цен акций успешно удалены.')
                    else:
                        stocks_errors_occurred = True; response_messages.append(
                            'Ошибка при удалении данных цен акций (функция вернула None).')
                except Exception as e:
                    stocks_errors_occurred = True; response_messages.append(
                        f'Внутренняя ошибка при удалении цен акций: {e}')
                try:
                    deleted_news_count = _internal_delete_all_news_articles()
                    if deleted_news_count is not None:
                        response_messages.append(f'{deleted_news_count} записей новостей успешно удалены.')
                    else:
                        news_errors_occurred = True; response_messages.append(
                        'Ошибка при удалении данных новостей (функция вернула None).')
                except Exception as e:
                    news_errors_occurred = True; response_messages.append(
                    f'Внутренняя ошибка при удалении новостей: {e}')
                final_message = "Результаты удаления: " + " | ".join(response_messages)
                # Добавляем акции в детали ответа
                response_data = {'message': final_message, 'details': {
                    'crypto_prices_deleted': deleted_crypto_count if deleted_crypto_count is not None else 'Ошибка/Не выполнено',
                    'asset_prices_deleted': deleted_assets_count if deleted_assets_count is not None else 'Ошибка/Не выполнено',
                    'stock_prices_deleted': deleted_stocks_count if deleted_stocks_count is not None else 'Ошибка/Не выполнено',
                    'news_deleted': deleted_news_count if deleted_news_count is not None else 'Ошибка/Не выполнено'}}
                # Добавляем проверку ошибки для акций
                if crypto_errors_occurred or assets_errors_occurred or stocks_errors_occurred or news_errors_occurred:
                    response_data['status'] = 'error'
                    return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    response_data['status'] = 'success'
                    return Response(response_data, status=status.HTTP_200_OK)

            elif command == 'delete_models':
                logger.info(f"[API] Обработка команды: {command}")
                models_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'trained_models')
                if not os.path.isdir(models_dir):
                    logger.warning(f"Папка для моделей '{models_dir}' не найдена. Нечего удалять.")
                    return Response({
                        'status': 'success',
                        'message': 'Папка для моделей не найдена, удаление не требуется.'
                    }, status=status.HTTP_200_OK)
                try:
                    deleted_items_count = 0
                    for item_name in os.listdir(models_dir):
                        item_path = os.path.join(models_dir, item_name)
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                            logger.info(f"Удален файл: {item_path}")
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            logger.info(f"Удалена директория: {item_path}")
                        deleted_items_count += 1
                    final_message = f'Модели успешно удалены.'
                    logger.info(final_message)
                    return Response({
                        'status': 'success',
                        'message': final_message
                    }, status=status.HTTP_200_OK)
                except Exception as e:
                    logger.exception(f"Критическая ошибка при удалении файлов из '{models_dir}':")
                    return Response({
                        'status': 'error',
                        'message': f'Не удалось очистить папку с моделями: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            else:
                logger.warning(f"[API] Получена неизвестная команда: {command}")
                raise ValidationError(f'Неизвестная команда: {command}')

        except ValidationError as e:
            error_msg_list = getattr(e, 'messages', None) or [str(e)]
            error_msg = "; ".join(error_msg_list)
            logger.warning(f"Ошибка валидации в ExecuteCommandAPIView: {error_msg}")
            return Response({'status': 'error', 'message': f'Ошибка валидации: {error_msg}'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Непредвиденная ошибка в ExecuteCommandAPIView:")
            return Response({'status': 'error', 'message': f'Внутренняя ошибка сервера: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Класс PredictCryptoAPIView ---
class PredictCryptoAPIView(APIView):
    """
    API для запуска команды predict_crypto (построение прогноза).
    """

    def post(self, request, *args, **kwargs):
        coin = request.data.get("coin")
        train_days_str = request.data.get("trainDays")
        predict_days_str = request.data.get("predictDays")
        predict_until_date_str = request.data.get("endDate")
        use_sentiment = request.data.get("useSentiment", False)
        sentiment_window_str = request.data.get("sentimentWindow", "3")
        sentiment_factor_str = request.data.get("sentimentFactor", "0.03")

        errors = {}
        if not coin: errors['coin'] = 'Параметр "coin" обязателен.'
        train_days = None
        try:
            train_days = int(train_days_str)
            if train_days <= 60: errors['trainDays'] = 'Параметр "trainDays" должен быть целым числом больше 60.'
        except (ValueError, TypeError):
            errors['trainDays'] = 'Параметр "trainDays" должен быть корректным целым числом.'
        predict_days = None
        try:
            predict_days = int(predict_days_str)
            if predict_days <= 0: errors[
                'predictDays'] = 'Параметр "predictDays" должен быть положительным целым числом.'
        except (ValueError, TypeError):
            errors['predictDays'] = 'Параметр "predictDays" должен быть корректным целым числом.'
        if predict_until_date_str:
            try:
                parse_date(predict_until_date_str)
            except (ValueError, TypeError):
                errors['endDate'] = 'Параметр "endDate" (predict_until_date) должен быть в формате YYYY-MM-DD.'
        sentiment_window = None
        sentiment_factor = None
        if use_sentiment:
            try:
                sentiment_window = int(sentiment_window_str)
                if sentiment_window <= 0: errors[
                    'sentimentWindow'] = 'Параметр "sentimentWindow" должен быть положительным целым числом.'
            except (ValueError, TypeError):
                errors['sentimentWindow'] = 'Параметр "sentimentWindow" должен быть корректным целым числом.'
            try:
                sentiment_factor = float(sentiment_factor_str)
            except (ValueError, TypeError):
                errors['sentimentFactor'] = 'Параметр "sentimentFactor" должен быть корректным числом.'
        if errors:
            logger.warning(f"Ошибки валидации в PredictCryptoAPIView: {errors}")
            error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            raise ValidationError(error_message)
        try:
            out = StringIO()
            err = StringIO()
            command_args = ['predict_crypto', '--coin', coin, '--train-days', str(train_days), '--predict-days',
                            str(predict_days)]
            if predict_until_date_str: command_args.extend(['--predict-until', predict_until_date_str])
            if use_sentiment:
                command_args.append('--use-sentiment')
                if sentiment_window is not None: command_args.extend(['--sentiment-window', str(sentiment_window)])
                if sentiment_factor is not None: command_args.extend(['--sentiment-factor', str(sentiment_factor)])
            logger.info(f"[*] Вызов команды прогнозирования: {' '.join(command_args)}")
            try:
                call_command(*command_args, stdout=out, stderr=err)
            except CommandError as cmd_e:
                logger.error(f"Ошибка выполнения команды predict_crypto: {cmd_e}. Stderr: {err.getvalue()}")
                return Response({'status': 'error', 'message': f'Ошибка выполнения команды прогнозирования: {cmd_e}',
                                 'details': err.getvalue()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            output_val = out.getvalue()
            errors_val = err.getvalue()
            if errors_val: logger.warning(f"Команда predict_crypto завершилась с сообщениями в stderr:\n{errors_val}")
            logger.debug(f"Команда predict_crypto stdout:\n{output_val}")
            match = re.search(r"PREDICTION_START\s*([\s\S]*?)\s*PREDICTION_END", output_val, re.MULTILINE)
            if match:
                json_output_str = match.group(1).strip()
                try:
                    predictions_data = json.loads(json_output_str)
                    return Response({'status': 'success', 'predictions': predictions_data, 'raw_output': output_val,
                                     'errors': errors_val if errors_val else None}, status=status.HTTP_200_OK)
                except json.JSONDecodeError as json_e:
                    logger.error(
                        f"Ошибка декодирования JSON из вывода predict_crypto: {json_e}. Вывод: {json_output_str}")
                    return Response(
                        {'status': 'error', 'message': f'Ошибка обработки результата предсказания (JSON): {json_e}',
                         'raw_output': output_val, 'errors': errors_val}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                error_message = f"Не удалось получить структурированный результат предсказания для {coin} (маркеры PREDICTION_START/END не найдены в выводе)."
                logger.error(f"{error_message} Raw output: {output_val}")
                return Response(
                    {'status': 'error', 'message': error_message, 'raw_output': output_val, 'errors': errors_val},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValidationError as e:
            error_msg_list = getattr(e, 'messages', None) or [str(e)]
            error_msg = "; ".join(error_msg_list)
            logger.warning(f"Ошибка валидации в PredictCryptoAPIView (внутренний try): {error_msg}")
            return Response({'status': 'error', 'message': f'Ошибка валидации параметров прогноза: {error_msg}'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при вызове команды predict_crypto для {coin}:")
            return Response(
                {'status': 'error', 'message': f'Внутренняя ошибка сервера при запуске предсказания: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Класс PredictAssetView ---
class PredictAssetView(APIView):
    """
    API для запуска команды predict_crypto (построение прогноза для ВАЛЮТНЫХ ПАР).
    """

    def post(self, request, *args, **kwargs):
        # Получаем данные из запроса
        asset_pair = request.data.get("asset_pair")
        train_days_str = request.data.get("trainDays")
        predict_days_str = request.data.get("predictDays")
        predict_until_date_str = request.data.get("endDate")

        # Валидация входных данных
        errors = {}
        if not asset_pair:
            errors['asset_pair'] = 'Параметр "asset_pair" обязателен.'

        train_days = None
        try:
            train_days = int(train_days_str)
            if train_days <= 60:
                errors['trainDays'] = 'Параметр "trainDays" должен быть целым числом больше 60.'
        except (ValueError, TypeError):
            errors['trainDays'] = 'Параметр "trainDays" должен быть корректным целым числом.'

        predict_days = None
        try:
            predict_days = int(predict_days_str)
            if predict_days <= 0:
                errors['predictDays'] = 'Параметр "predictDays" должен быть положительным целым числом.'
        except (ValueError, TypeError):
            errors['predictDays'] = 'Параметр "predictDays" должен быть корректным целым числом.'

        if predict_until_date_str:
            try:
                parse_date(predict_until_date_str)
            except (ValueError, TypeError):
                errors['endDate'] = 'Параметр "endDate" должен быть в формате YYYY-MM-DD.'

        if errors:
            logger.warning(f"Ошибки валидации в PredictAssetView: {errors}")
            error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            return Response({'status': 'error', 'message': f'Ошибка валидации: {error_message}'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            out = StringIO()
            err = StringIO()

            command_args = [
                'predict_crypto',
                '--asset-pair', asset_pair,
                '--train-days', str(train_days),
                '--predict-days', str(predict_days)
            ]
            if predict_until_date_str:
                command_args.extend(['--predict-until', predict_until_date_str])

            logger.info(f"[*] Вызов команды прогнозирования для валют: {' '.join(command_args)}")

            call_command(*command_args, stdout=out, stderr=err)

            output_val = out.getvalue()
            errors_val = err.getvalue()

            if errors_val:
                logger.warning(f"Команда predict_crypto для валют завершилась с сообщениями в stderr:\n{errors_val}")

            match = re.search(r"PREDICTION_START\s*([\s\S]*?)\s*PREDICTION_END", output_val, re.MULTILINE)
            if match:
                json_output_str = match.group(1).strip()
                try:
                    predictions_data = json.loads(json_output_str)
                    return Response({'status': 'success', 'predictions': predictions_data})
                except json.JSONDecodeError as json_e:
                    logger.error(
                        f"Ошибка декодирования JSON из вывода predict_crypto (для валют): {json_e}. Вывод: {json_output_str}")
                    return Response({'status': 'error', 'message': f'Ошибка обработки результата: {json_e}'},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                error_message = f"Не удалось получить результат предсказания для {asset_pair} (маркеры PREDICTION_START/END не найдены)."
                logger.error(f"{error_message} Raw output: {output_val}")
                return Response({'status': 'error', 'message': error_message},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при вызове команды для {asset_pair}:")
            return Response({'status': 'error', 'message': f'Внутренняя ошибка сервера: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Класс PredictStockView ---
class PredictStockView(APIView):
    """
    API для запуска команды прогнозирования для АКЦИЙ.
    Предполагается, что команда predict_crypto может принимать параметр --ticker.
    """

    def post(self, request, *args, **kwargs):
        # Получаем данные из запроса
        ticker = request.data.get("ticker")
        train_days_str = request.data.get("trainDays")
        predict_days_str = request.data.get("predictDays")
        predict_until_date_str = request.data.get("endDate")

        # Валидация входных данных
        errors = {}
        if not ticker:
            errors['ticker'] = 'Параметр "ticker" обязателен.'

        train_days = None
        try:
            train_days = int(train_days_str)
            if train_days <= 60:
                errors['trainDays'] = 'Параметр "trainDays" должен быть целым числом больше 60.'
        except (ValueError, TypeError):
            errors['trainDays'] = 'Параметр "trainDays" должен быть корректным целым числом.'

        predict_days = None
        try:
            predict_days = int(predict_days_str)
            if predict_days <= 0:
                errors['predictDays'] = 'Параметр "predictDays" должен быть положительным целым числом.'
        except (ValueError, TypeError):
            errors['predictDays'] = 'Параметр "predictDays" должен быть корректным целым числом.'

        if predict_until_date_str:
            try:
                parse_date(predict_until_date_str)
            except (ValueError, TypeError):
                errors['endDate'] = 'Параметр "endDate" должен быть в формате YYYY-MM-DD.'

        if errors:
            logger.warning(f"Ошибки валидации в PredictStockView: {errors}")
            error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            return Response({'status': 'error', 'message': f'Ошибка валидации: {error_message}'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            out = StringIO()
            err = StringIO()

            command_args = [
                'predict_crypto',
                '--ticker', ticker,
                '--train-days', str(train_days),
                '--predict-days', str(predict_days)
            ]
            if predict_until_date_str:
                command_args.extend(['--predict-until', predict_until_date_str])

            logger.info(f"[*] Вызов команды прогнозирования для акций: {' '.join(command_args)}")

            try:
                call_command(*command_args, stdout=out, stderr=err)
            except CommandError as cmd_e:
                logger.error(f"Ошибка выполнения команды predict_crypto для акций: {cmd_e}. Stderr: {err.getvalue()}")
                return Response({'status': 'error', 'message': f'Ошибка выполнения команды прогнозирования: {cmd_e}',
                                 'details': err.getvalue()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            output_val = out.getvalue()
            errors_val = err.getvalue()

            if errors_val:
                logger.warning(f"Команда predict_crypto для акций завершилась с сообщениями в stderr:\n{errors_val}")

            match = re.search(r"PREDICTION_START\s*([\s\S]*?)\s*PREDICTION_END", output_val, re.MULTILINE)
            if match:
                json_output_str = match.group(1).strip()
                try:
                    predictions_data = json.loads(json_output_str)
                    return Response({'status': 'success', 'predictions': predictions_data,
                                     'errors': errors_val if errors_val else None}, status=status.HTTP_200_OK)
                except json.JSONDecodeError as json_e:
                    logger.error(
                        f"Ошибка декодирования JSON из вывода predict_crypto (для акций): {json_e}. Вывод: {json_output_str}")
                    return Response({'status': 'error', 'message': f'Ошибка обработки результата: {json_e}',
                                     'raw_output': output_val, 'errors': errors_val},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                error_message = f"Не удалось получить результат предсказания для {ticker} (маркеры PREDICTION_START/END не найдены)."
                logger.error(f"{error_message} Raw output: {output_val}")
                return Response({'status': 'error', 'message': error_message, 'raw_output': output_val,
                                 'errors': errors_val}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при вызове команды для {ticker}:")
            return Response({'status': 'error', 'message': f'Внутренняя ошибка сервера: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)