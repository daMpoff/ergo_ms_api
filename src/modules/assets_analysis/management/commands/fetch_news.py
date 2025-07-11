import feedparser
import requests
import logging
import datetime

from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz
from django.utils.dateparse import parse_datetime, parse_date
from django.db import transaction

from src.modules.assets_analysis.models import NewsArticle
from src.modules.assets_analysis.scripts import SELECTED_COINS


try:
    import torch

    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    
    ML_IMPORTED = True
except ImportError as e:
    ML_IMPORTED = False
    ML_IMPORT_ERROR_MSG = str(e)

logger = logging.getLogger(__name__)


DEFAULT_NEWS_DAYS = 30
NEWS_SOURCES = {
    'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'Cointelegraph': 'https://cointelegraph.com/rss',
    'CryptoNews': 'https://cryptonews.com/news/feed/',
    'Forklog': 'https://forklog.com/feed',
}

SENTIMENT_MODEL_NAME = 'blanchefort/rubert-base-cased-sentiment'
MAX_SEQ_LENGTH = 512
# Генерация ключевых слов для поиска монет
COIN_KEYWORDS = {name: [name, data['coingecko']] + name.split('-')
                 for name, data in SELECTED_COINS.items()}
for name, data in SELECTED_COINS.items():
    ticker = data.get('binance', '').replace('USDT', '').lower()
    if ticker and ticker not in COIN_KEYWORDS[name]:
        COIN_KEYWORDS[name].append(ticker)
COIN_KEYWORDS['bitcoin'].extend(['биткоин', 'биткойн', 'btc'])
COIN_KEYWORDS['ethereum'].extend(['эфириум', 'эфир', 'eth'])

class Command(BaseCommand):
    help = ('Скачивает новости из RSS-фидов, анализирует тональность и сохраняет в БД. '
            'Работает по диапазону дат (--start-date/--end-date) или за последние N дней (--days).')

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=DEFAULT_NEWS_DAYS,
            help=(f'За сколько последних дней скачивать новости (по умолчанию: {DEFAULT_NEWS_DAYS}). '
                  f'Игнорируется, если указаны --start-date.')
        )
        parser.add_argument(
            '--start-date',
            type=str,
            default=None,
            help='Начальная дата для скачивания новостей (YYYY-MM-DD). Переопределяет --days.'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            default=None,
            help=('Конечная дата для скачивания новостей (YYYY-MM-DD). Используется с --start-date. '
                  'По умолчанию - сегодня.')
        )
        parser.add_argument(
            '--min-age-hours',
            type=int,
            default=0,
            help='Минимальный возраст новости в часах (чтобы не перескачивать слишком часто). По умолчанию 0.'
        )
        parser.add_argument(
            '--sources',
            nargs='+',
            default=list(NEWS_SOURCES.keys()),
            help='Названия источников для скачивания (из списка NEWS_SOURCES). Пример: --sources CoinDesk Forklog'
        )
        parser.add_argument(
            '--skip-sentiment',
            action='store_true',
            help='Пропустить анализ тональности (только скачать и сохранить новости).'
        )
        parser.add_argument(
            '--force-rescan',
            action='store_true',
            help='Повторно проанализировать существующие новости в указанном диапазоне дат (без скачивания).'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер батча для сохранения новостей в БД.'
        )

    def _load_model_and_tokenizer(self):
        """Загружает модель и токенизатор для анализа тональности."""
        if not ML_IMPORTED:
            raise CommandError(
                f"Необходимые ML библиотеки не установлены: {ML_IMPORT_ERROR_MSG}. Установите torch и transformers.")

        self.stdout.write(f"[*] Загрузка модели анализа тональности: {SENTIMENT_MODEL_NAME}...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL_NAME)
            # Определяем устройство (GPU если доступно, иначе CPU)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            model.eval() # Переводим модель в режим оценки
            self.stdout.write(self.style.SUCCESS(f"[*] Модель загружена и работает на устройстве: {device}"))
            return tokenizer, model, device
        except Exception as e:
            raise CommandError(f"Ошибка загрузки модели {SENTIMENT_MODEL_NAME}: {e}")

    def _analyze_sentiment(self, text, tokenizer, model, device):
        """Анализирует тональность одного текста с помощью загруженной модели."""
        # Проверка входных данных
        if not text or not tokenizer or not model or not device:
            return None, 'skipped'

        try:
            # Токенизация текста
            inputs = tokenizer(
                text,
                return_tensors='pt', # Возвращаем PyTorch тензоры
                truncation=True,     # Обрезаем текст, если он длиннее max_length
                padding=True,        # Дополняем короткие тексты до max_length
                max_length=MAX_SEQ_LENGTH
            ).to(device) # Перемещаем тензоры на нужное устройство (CPU/GPU)

            # Получение предсказаний модели
            with torch.no_grad(): # Отключаем расчет градиентов для экономии памяти
                outputs = model(**inputs)
                logits = outputs.logits

            # Преобразование логитов в вероятности и определение метки
            probabilities = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            label_map = model.config.id2label # Получаем маппинг ID классов в метки ( {0: 'negative', ...})
            predicted_class_id = probabilities.argmax().item()
            predicted_label = label_map.get(predicted_class_id, 'neutral')

            # Расчет скора (разница между positive и negative вероятностями)
            pos_index = next((k for k, v in label_map.items() if v.lower() == 'positive'), -1)
            neg_index = next((k for k, v in label_map.items() if v.lower() == 'negative'), -1)

            score = 0.0
            if pos_index != -1 and neg_index != -1:
                # Стандартный расчет, если есть и positive, и negative метки
                score = probabilities[pos_index] - probabilities[neg_index]
            elif pos_index != -1: # Если есть только positive (например, в 2-классовой модели)
                score = probabilities[pos_index] * 0.5
            elif neg_index != -1: # Если есть только negative
                score = -probabilities[neg_index] * 0.5

            # Нормализация метки и предупреждение о неожиданных метках
            final_label = predicted_label.lower()
            if final_label not in ['positive', 'negative', 'neutral']:
                logger.warning(f"Модель вернула неожиданную метку: {predicted_label}. Используется 'neutral'.")
                final_label = 'neutral'

            return score, final_label

        except Exception as e:
            logger.error(f"Ошибка анализа тональности для текста '{text[:50]}...': {e}", exc_info=True)
            return None, 'skipped'

    def _find_relevant_coins(self, text):
        """Определяет, какие монеты упоминаются в тексте."""
        if not text:
            return []

        text_lower = text.lower()
        found_coins = set()
        # Итерация по словарю монет и их ключевых слов
        for coin_name, keywords in COIN_KEYWORDS.items():
            for keyword in keywords:
                # Простая проверка вхождения ключевого слова
                if keyword.lower() in text_lower:
                    found_coins.add(coin_name)
                    break # Переходим к следующей монете, если одно слово найдено
        return sorted(list(found_coins)) # Возвращаем отсортированный список уникальных имен

    def _clean_html(self, html_content):
        """Простая очистка HTML из описания новости с помощью BeautifulSoup."""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # Извлекаем текст, заменяя теги на пробелы и удаляя лишние пробелы
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            # Логгируем предупреждение и возвращаем исходный HTML в случае ошибки
            logger.warning(f"Ошибка очистки HTML: {e}")
            return html_content

    def handle(self, *args, **options):
        days_delta = options['days']
        min_age_hours = options['min_age_hours']
        selected_source_names = options['sources']
        skip_sentiment = options['skip_sentiment']
        force_rescan = options['force_rescan']
        batch_size = options['batch_size']
        start_date_str = options['start_date']
        end_date_str = options['end_date']

        # --- Определение временного диапазона для обработки ---
        now = tz.now() # Текущее время с учетом таймзоны Django
        start_datetime = None
        end_datetime = None

        if start_date_str:
            # Если задана начальная дата, используем режим диапазона дат
            self.stdout.write("[*] Используется режим диапазона дат (--start-date / --end-date).")
            try:
                # Парсим начальную дату
                start_dt_naive = parse_date(start_date_str)
                if not start_dt_naive: raise ValueError("Начальная дата не распознана")
                start_datetime = tz.make_aware(datetime.datetime.combine(start_dt_naive, datetime.time.min), datetime.timezone.utc)
                # Парсим конечную дату (если не задана, используем сегодня)
                end_dt_naive = parse_date(end_date_str) if end_date_str else now.date()
                if not end_dt_naive: raise ValueError("Конечная дата не распознана")
                end_datetime = tz.make_aware(datetime.datetime.combine(end_dt_naive, datetime.time.max), datetime.timezone.utc)

                # Проверка корректности диапазона
                if start_datetime > end_datetime:
                    raise CommandError("Начальная дата (--start-date) не может быть позже конечной (--end-date).")

                self.stdout.write(
                    f"[*] Диапазон обработки: с {start_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                    f"по {end_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            except (ValueError, TypeError) as e:
                raise CommandError(f"Неверный формат даты для --start-date или --end-date: {e}. Используйте YYYY-MM-DD.")
        else:
            # Если начальная дата не задана, используем режим --days
            self.stdout.write(f"[*] Используется режим последних N дней (--days={days_delta}).")
            end_datetime = now # Конец диапазона - текущий момент
            start_datetime = end_datetime - datetime.timedelta(days=days_delta)
            self.stdout.write(
                f"[*] Диапазон обработки: с {start_datetime.strftime('%Y-%m-%d %H:%M')} "
                f"по {end_datetime.strftime('%Y-%m-%d %H:%M')}"
            )

        # Определяем минимальную дату публикации (для опции --min-age-hours)
        min_publish_datetime = now - datetime.timedelta(hours=min_age_hours) if min_age_hours > 0 else None
        if min_publish_datetime:
             self.stdout.write(f"[*] Пропускаются новости новее {min_publish_datetime.strftime('%Y-%m-%d %H:%M')}")

        # --- Загрузка ML модели ---
        tokenizer, model, device = None, None, None
        if not skip_sentiment or force_rescan:
             if not ML_IMPORTED:
                 self.stderr.write(self.style.ERROR(f"[-] ML библиотеки не найдены: {ML_IMPORT_ERROR_MSG}"))
                 self.stderr.write(
                     self.style.ERROR("[-] Установите torch и transformers или используйте флаг --skip-sentiment / не используйте --force-rescan."))
                 return
             try:
                 # Загружаем модель и токенизатор
                 tokenizer, model, device = self._load_model_and_tokenizer()
             except CommandError as e:
                 # Ошибка при загрузке модели
                 self.stderr.write(self.style.ERROR(f"[-] {e}"))
                 return

        # --- Логика повторного анализа (force_rescan) ---
        if force_rescan:
            if skip_sentiment:
                self.stderr.write(self.style.ERROR("[-] Нельзя использовать --force-rescan вместе с --skip-sentiment."))
                return

            self.stdout.write(self.style.WARNING(
                f"[*] Запуск повторного анализа тональности существующих новостей в диапазоне "
                f"{start_datetime.strftime('%Y-%m-%d')} - {end_datetime.strftime('%Y-%m-%d')}..."
            ))
            # Выбираем новости из БД в заданном диапазоне дат
            articles_to_rescan = NewsArticle.objects.filter(
                published_at__gte=start_datetime,
                published_at__lte=end_datetime
            ).order_by('published_at')

            rescan_updated = 0
            rescan_skipped = 0
            total_to_rescan = articles_to_rescan.count()
            self.stdout.write(f"[*] Найдено {total_to_rescan} новостей для повторного анализа.")

            articles_to_bulk_update = [] # Список для массового обновления
            for i, article in enumerate(articles_to_rescan):
                if (i + 1) % 100 == 0: # Логгируем прогресс каждые 100 новостей
                    self.stdout.write(f"[*] Повторный анализ: обработано {i + 1} / {total_to_rescan}...")

                # Формируем текст для анализа (заголовок + очищенное содержание)
                text_to_analyze = f"{article.title}. {self._clean_html(article.summary or '')}".strip()
                # Анализируем тональность
                score, label = self._analyze_sentiment(text_to_analyze, tokenizer, model, device)

                if label != 'skipped': # Если анализ прошел успешно
                    # Проверяем, изменился ли скор или метка
                    if article.sentiment_score != score or article.sentiment_label != label:
                        article.sentiment_score = score
                        article.sentiment_label = label
                        articles_to_bulk_update.append(article) # Добавляем в список для обновления
                        rescan_updated += 1
                    else:
                        rescan_skipped += 1 # Не изменилось
                else:
                    rescan_skipped += 1 # Анализ не удался

                # Периодическое сохранение батча обновлений
                if len(articles_to_bulk_update) >= batch_size:
                    try:
                        NewsArticle.objects.bulk_update(articles_to_bulk_update, ['sentiment_score', 'sentiment_label'])
                        self.stdout.write(
                            f"[*] Повторный анализ: сохранено {len(articles_to_bulk_update)} обновлений в БД.")
                        articles_to_bulk_update = []
                    except Exception as e:
                        logger.error(f"Ошибка bulk_update при повторном анализе: {e}")
                        self.stderr.write(
                            self.style.ERROR(f"[-] Ошибка сохранения обновлений при повторном анализе: {e}"))

            if articles_to_bulk_update:
                try:
                    NewsArticle.objects.bulk_update(articles_to_bulk_update, ['sentiment_score', 'sentiment_label'])
                    self.stdout.write(
                        f"[*] Повторный анализ: сохранено последних {len(articles_to_bulk_update)} обновлений в БД.")
                except Exception as e:
                    logger.error(f"Ошибка bulk_update при повторном анализе (финал): {e}")
                    self.stderr.write(
                        self.style.ERROR(f"[-] Ошибка сохранения последних обновлений при повторном анализе: {e}"))

            # Отчет по итогам рескана
            self.stdout.write(self.style.SUCCESS(
                f"[*] Повторный анализ завершен. Обновлено: {rescan_updated}, Пропущено/Без изменений: {rescan_skipped}"))
            return

        # --- Основной цикл скачивания и обработки новостей ---
        added_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        processed_urls = set() # Храним URL обработанных новостей для избежания дублей в рамках одного запуска
        articles_to_bulk_create = [] # Список для новых статей
        articles_to_bulk_update_sentiment = [] # Список для обновления сентимента существующих

        # Итерация по источникам новостей
        for source_name, source_url in NEWS_SOURCES.items():
            if source_name not in selected_source_names: # Пропускаем источник, если он не выбран
                continue

            self.stdout.write(f"\n[*] Получение новостей из источника: {source_name} ({source_url})")
            try:
                # Используем requests для получения фида с User-Agent
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; YourAppBot/1.0; +http://yourapp.com/bot)'}
                response = requests.get(source_url, headers=headers, timeout=30) # Таймаут 30 секунд
                response.raise_for_status() # Проверка на HTTP ошибки (4xx, 5xx)
                # Парсим полученный контент с помощью feedparser
                feed = feedparser.parse(response.content)

                # Проверка на ошибки парсинга самого фида
                if feed.bozo:
                    logger.warning(f"Источник {source_name} вернул ошибку парсинга RSS/Atom: {feed.bozo_exception}")

                if not feed.entries:
                    self.stdout.write(self.style.WARNING(f"[-] Нет записей в фиде {source_name}."))
                    continue

                self.stdout.write(f"[*] Найдено {len(feed.entries)} записей в фиде.")

                # Обработка каждой записи (новости) в фиде
                for entry in feed.entries:
                    entry_url = getattr(entry, 'link', None) # Получаем URL новости
                    # Пропускаем, если нет URL или он уже обработан
                    if not entry_url or entry_url in processed_urls:
                        skipped_count += 1
                        continue

                    # --- Парсинг даты публикации новости из фида ---
                    published_time_parsed = None # Инициализация
                    # Пытаемся получить распарсенную дату из feedparser
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            # Преобразуем time.struct_time в наивный datetime
                            naive_dt = datetime.datetime(*entry.published_parsed[:6])
                            # Делаем datetime "осведомленным" (aware) в UTC
                            published_time_parsed = tz.make_aware(naive_dt, datetime.timezone.utc)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Не удалось создать datetime из published_parsed для {entry_url}. Ошибка: {e}. Значение: {entry.published_parsed}")
                        except Exception as e: # Ловим другие возможные ошибки
                             logger.error(f"Неожиданная ошибка при обработке published_parsed для {entry_url}: {e}", exc_info=True)
                    # Если published_parsed не сработал, пытаемся распарсить строку 'published'
                    elif hasattr(entry, 'published'):
                         try:
                             # Используем parse_datetime из Django для большей гибкости
                             parsed_dt_maybe_aware = parse_datetime(entry.published)
                             if parsed_dt_maybe_aware:
                                 if tz.is_aware(parsed_dt_maybe_aware):
                                     published_time_parsed = parsed_dt_maybe_aware
                                 else:
                                     published_time_parsed = tz.make_aware(parsed_dt_maybe_aware, datetime.timezone.utc)
                             else:
                                logger.warning(f"Не удалось распарсить строку 'published' для {entry_url}: '{entry.published}'")
                         except Exception as e:
                             logger.error(f"Ошибка при парсинге строки 'published' для {entry_url}: {e}", exc_info=True)

                    # Если не удалось получить дату из фида, используем текущее время
                    if not published_time_parsed:
                        published_time_parsed = tz.now()
                        logger.warning(
                            f"Не удалось определить дату публикации для {entry_url} из фида, используется текущее время.")

                    # --- Фильтрация новости по дате ---
                    # Сравниваем aware datetime новости с aware datetime границами диапазона
                    if published_time_parsed < start_datetime:
                        # self.stdout.write(f"Debug: Skipping OLD {entry_url} ({published_time_parsed})")
                        skipped_count += 1
                        continue
                    if published_time_parsed > end_datetime:
                        # self.stdout.write(f"Debug: Skipping FUTURE {entry_url} ({published_time_parsed})")
                        skipped_count += 1
                        continue
                    if min_publish_datetime and published_time_parsed > min_publish_datetime:
                        # self.stdout.write(f"Debug: Skipping TOO NEW {entry_url} ({published_time_parsed})")
                        skipped_count += 1
                        continue

                    # Получаем заголовок и содержание новости
                    title = getattr(entry, 'title', 'Без заголовка')
                    summary_html = getattr(entry, 'summary', getattr(entry, 'description', '')) # Пробуем summary, потом description
                    summary_text = self._clean_html(summary_html) # Очищаем HTML
                    # Текст для анализа тональности (заголовок + содержание)
                    text_for_analysis = f"{title}. {summary_text}".strip()

                    try:
                        # Пытаемся найти новость в БД по URL
                        existing_article = NewsArticle.objects.get(url=entry_url)
                        processed_urls.add(entry_url) # Отмечаем URL как обработанный

                        if not skip_sentiment and existing_article.sentiment_label == 'skipped':
                            score, label = self._analyze_sentiment(text_for_analysis, tokenizer, model, device)
                            if label != 'skipped':
                                existing_article.sentiment_score = score
                                existing_article.sentiment_label = label
                                articles_to_bulk_update_sentiment.append(existing_article)
                                updated_count += 1
                            else:
                                skipped_count += 1 # Анализ не удался, пропускаем
                        else:
                            # Новость существует, но сентимент обновлять не нужно (уже есть или skip_sentiment)
                            skipped_count += 1

                    except NewsArticle.DoesNotExist:
                        # Если новость не найдена в БД - это новая новость
                        processed_urls.add(entry_url) # Отмечаем URL как обработанный
                        # Определяем релевантные монеты
                        relevant_coins = self._find_relevant_coins(text_for_analysis)

                        # Анализируем тональность, если не пропускаем
                        score, label = None, 'skipped'
                        if not skip_sentiment:
                            score, label = self._analyze_sentiment(text_for_analysis, tokenizer, model, device)
                            # Если анализ не удался, score останется None, label 'skipped'

                        # Создаем объект новой статьи
                        new_article = NewsArticle(
                            title=title,
                            url=entry_url,
                            source=source_name,
                            summary=summary_text,
                            published_at=published_time_parsed,
                            relevant_coins=relevant_coins,
                            sentiment_score=score,
                            sentiment_label=label
                        )
                        articles_to_bulk_create.append(new_article) # Добавляем в список для создания
                        added_count += 1

                    except Exception as e: # Обработка других ошибок при работе с БД или анализе
                        logger.error(f"Ошибка обработки записи {entry_url} из {source_name}: {e}", exc_info=True)
                        error_count += 1
                        skipped_count += 1 # Считаем как пропущенную из-за ошибки

                # --- Сохранение батчей после обработки одного источника ---
                if len(articles_to_bulk_create) >= batch_size:
                    try:
                        # Используем транзакцию для атомарности
                        with transaction.atomic():
                            NewsArticle.objects.bulk_create(articles_to_bulk_create, ignore_conflicts=True)
                            self.stdout.write(f"[*] Сохранено {len(articles_to_bulk_create)} новых новостей в БД.")
                        articles_to_bulk_create = []
                    except Exception as e:
                        logger.error(f"Ошибка bulk_create: {e}")
                        self.stderr.write(self.style.ERROR(f"[-] Ошибка сохранения новых новостей: {e}"))
                        articles_to_bulk_create = []

                if len(articles_to_bulk_update_sentiment) >= batch_size:
                    try:
                        with transaction.atomic():
                            NewsArticle.objects.bulk_update(articles_to_bulk_update_sentiment,
                                                            ['sentiment_score', 'sentiment_label'])
                            self.stdout.write(
                                f"[*] Обновлен сентимент для {len(articles_to_bulk_update_sentiment)} новостей в БД.")
                        articles_to_bulk_update_sentiment = []
                    except Exception as e:
                        logger.error(f"Ошибка bulk_update sentiment: {e}")
                        self.stderr.write(self.style.ERROR(f"[-] Ошибка обновления сентимента новостей: {e}"))
                        articles_to_bulk_update_sentiment = []

            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка сети при запросе к {source_name}: {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"Неожиданная ошибка при обработке источника {source_name}: {e}", exc_info=True)
                error_count += 1


        if articles_to_bulk_create:
            try:
                with transaction.atomic():
                    NewsArticle.objects.bulk_create(articles_to_bulk_create, ignore_conflicts=True)
                    self.stdout.write(f"[*] Сохранено последних {len(articles_to_bulk_create)} новых новостей в БД.")
            except Exception as e:
                logger.error(f"Ошибка bulk_create (финал): {e}")
                self.stderr.write(self.style.ERROR(f"[-] Ошибка сохранения последних новых новостей: {e}"))

        if articles_to_bulk_update_sentiment:
            try:
                with transaction.atomic():
                    NewsArticle.objects.bulk_update(articles_to_bulk_update_sentiment,
                                                    ['sentiment_score', 'sentiment_label'])
                    self.stdout.write(
                        f"[*] Обновлен сентимент для последних {len(articles_to_bulk_update_sentiment)} новостей в БД.")
            except Exception as e:
                logger.error(f"Ошибка bulk_update sentiment (финал): {e}")
                self.stderr.write(self.style.ERROR(f"[-] Ошибка обновления сентимента последних новостей: {e}"))

        self.stdout.write("\n--- Итоги ---")
        self.stdout.write(self.style.SUCCESS(f"Добавлено новых новостей: {added_count}"))
        self.stdout.write(f"Обновлен сентимент (у существующих): {updated_count}")
        self.stdout.write(f"Пропущено (дубликаты, вне диапазона дат, ошибки, без изменений): {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Ошибки обработки (сеть/парсер/БД): {error_count}"))
        else:
            self.stdout.write("Ошибки обработки: 0")
        self.stdout.write(self.style.SUCCESS("[*] Сканирование новостей завершено."))