# Парсер ФГОС

Парсер для автоматического сбора документов Федеральных государственных образовательных стандартов (ФГОС) с сайта [fgos.ru](https://fgos.ru/).

## Возможности

- 🔍 Автоматический поиск всех страниц ФГОС на сайте
- 📄 Парсинг метаданных документов (название, код специальности, уровень образования и т.д.)
- 📥 Скачивание PDF файлов ФГОС с уникальными UUID именами
- 🗄️ Сохранение информации в базе данных с полной трассировкой
- 📊 Отслеживание сессий парсинга со статистикой
- 🔄 Обновление существующих документов
- 🧹 Очистка файлов-сирот

## Модели данных

### FgosDocument
Основная модель для хранения информации о документах ФГОС:

- `uuid` - уникальный идентификатор файла
- `title` - название ФГОС
- `code` - код специальности (например, "37.05.02")
- `level` - уровень образования (бакалавриат, магистратура, специалитет и т.д.)
- `field_of_study` - область изучения
- `filename` - имя файла
- `file_size` - размер файла в байтах
- `source_url` - исходная ссылка на страницу
- `download_url` - ссылка для скачивания PDF
- `published_date` - дата публикации
- `parsed_at` - время парсинга
- `is_downloaded` - статус скачивания файла
- `download_error` - текст ошибки скачивания (если есть)
- `order_number` - номер приказа
- `ministry` - министерство
- `registration_number` - регистрационный номер

### FgosParsingSession
Модель для отслеживания сессий парсинга:

- `id` - UUID сессии
- `started_at` / `finished_at` - время начала и окончания
- `total_pages_found` - всего найдено страниц
- `total_documents_found` - всего найдено документов
- `new_documents_added` - добавлено новых документов
- `documents_updated` - обновлено документов
- `files_downloaded` - скачано файлов
- `download_errors` - ошибок скачивания
- `status` - статус сессии (running, completed, failed, cancelled)
- `error_message` - сообщение об ошибке

## Использование

### Management команды

#### Полный парсинг
```bash
python src/manage.py parse_fgos --full
```

#### Скачивание недостающих файлов
```bash
python src/manage.py parse_fgos --download-missing
```

#### Обновление существующих документов
```bash
python src/manage.py parse_fgos --update-existing
```

#### Очистка файлов-сирот
```bash
python src/manage.py parse_fgos --cleanup-files
```

#### Показать статистику
```bash
python src/manage.py parse_fgos --show-stats
```

#### Парсинг конкретной страницы
```bash
python src/manage.py parse_fgos --url "https://fgos.ru/fgos/fgos-37-05-02-psihologiya-sluzhebnoy-deyatelnosti-uroven-specialiteta-1613/"
```

### Celery задачи

Парсер также предоставляет Celery задачи для асинхронного выполнения:

```python
from src.modules.education_materials_parser.fgos.tasks import (
    parse_all_fgos_documents,
    download_missing_fgos_files,
    update_existing_fgos_documents,
    cleanup_orphaned_fgos_files
)

# Запуск полного парсинга
result = parse_all_fgos_documents.delay()

# Скачивание недостающих файлов
result = download_missing_fgos_files.delay()

# Обновление существующих документов
result = update_existing_fgos_documents.delay()

# Очистка файлов-сирот
result = cleanup_orphaned_fgos_files.delay()
```

### Программное использование

```python
from src.modules.education_materials_parser.fgos.scripts import FgosParser

# Создание парсера
parser = FgosParser()

# Запуск полного парсинга
session = parser.run_full_parsing()

# Парсинг конкретной страницы
document_data = parser.parse_fgos_page('https://fgos.ru/fgos/fgos-37-05-02-...')

# Поиск ссылок на ФГОС
links = parser.find_fgos_links()
```

## Хранение файлов

Все PDF файлы сохраняются в папке `media/education_materials_parser/` с именами в формате `{UUID}.pdf`.

Например: `123e4567-e89b-12d3-a456-426614174000.pdf`

Найти файл можно по UUID из модели `FgosDocument`:

```python
from src.modules.education_materials_parser.fgos.models import FgosDocument
import os
from django.conf import settings

doc = FgosDocument.objects.get(code="37.05.02")
file_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
# file_path будет: /path/to/media/education_materials_parser/123e4567-e89b-12d3-a456-426614174000.pdf
```

## Архитектура парсера

### Стратегии поиска ссылок

Парсер использует несколько стратегий для поиска страниц ФГОС:

1. **Сканирование основных разделов** - проверка `/fgos/` и главной страницы
2. **Поиск через карту сайта** - проверка `sitemap.xml` и других карт сайта
3. **Прямой поиск по кодам** - генерация URL на основе известных кодов специальностей
4. **Тестовые ссылки** - использование известных рабочих ссылок как fallback

### Извлечение данных

Для каждой страницы ФГОС парсер извлекает:

- Заголовок документа из `<h1>` или `<title>`
- Код специальности через regex паттерны
- Уровень образования по ключевым словам
- Ссылку на скачивание PDF (поиск по тексту "Скачать" и `standart_pdf.php`)
- Номер приказа, министерство, регистрационный номер через regex
- Дату публикации в различных форматах

### Скачивание файлов

- Проверка типа содержимого (Content-Type)
- Валидация PDF заголовка (`%PDF`)
- Сохранение с уникальным UUID именем
- Отслеживание размера файла и ошибок

## Настройки

Основные настройки парсера:

```python
# В scripts.py класс FgosParser
self.base_url = "https://fgos.ru"
self.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
}

# Таймауты
timeout=30  # для получения страниц
timeout=60  # для скачивания файлов

# Задержки между запросами
time.sleep(2)  # в основном парсинге
time.sleep(1)  # при поиске ссылок
time.sleep(0.5)  # при проверке прямых ссылок
```

## Обработка ошибок

Парсер устойчив к ошибкам:

- Пропуск недоступных страниц
- Продолжение работы при ошибках скачивания
- Сохранение текста ошибок в БД
- Отслеживание статистики ошибок в сессиях

## Требования

- Python 3.8+
- Django 3.2+
- BeautifulSoup4
- requests
- Celery (для асинхронных задач)

## Примеры использования

### Получение статистики через код

```python
from src.modules.education_materials_parser.fgos.models import FgosDocument, FgosParsingSession

# Общая статистика
total_docs = FgosDocument.objects.count()
downloaded = FgosDocument.objects.filter(is_downloaded=True).count()
failed = FgosDocument.objects.filter(is_downloaded=False).count()

print(f"Всего: {total_docs}, Скачано: {downloaded}, Ошибок: {failed}")

# Статистика по уровням
from django.db.models import Count
stats = FgosDocument.objects.values('level').annotate(count=Count('id'))
for stat in stats:
    print(f"{stat['level']}: {stat['count']}")

# Последние сессии
recent = FgosParsingSession.objects.order_by('-started_at')[:5]
for session in recent:
    print(f"{session.started_at} - {session.status} - {session.files_downloaded} файлов")
```

### Поиск документов

```python
# По коду специальности
doc = FgosDocument.objects.filter(code="37.05.02").first()

# По уровню образования
docs = FgosDocument.objects.filter(level="Специалитет")

# По области изучения
docs = FgosDocument.objects.filter(field_of_study__icontains="психология")

# Только скачанные файлы
docs = FgosDocument.objects.filter(is_downloaded=True)

# С ошибками скачивания
failed_docs = FgosDocument.objects.filter(is_downloaded=False).exclude(download_error__isnull=True)
``` 