# Парсер вакансий SuperJob

Модуль для парсинга вакансий с сайта SuperJob через их API.

## Возможности

- Парсинг вакансий по текстовым запросам
- Универсальный парсинг по популярным запросам
- Получение детальной информации о конкретных вакансиях
- Сохранение в базу данных с версионностью
- Асинхронная обработка через Celery
- Поддержка фильтров (город, опыт, тип занятости, график работы)

## Установка и настройка

### 1. Получение API ключа SuperJob

Для работы с API SuperJob необходимо получить API ключ:
1. Зарегистрируйтесь на [SuperJob](https://www.superjob.ru/)
2. Перейдите в раздел для разработчиков
3. Получите API ключ

### 2. Настройка конфигурации

Отредактируйте файл `management/commands/config.json`:

```json
{
  "api_key": "ваш_api_ключ_superjob",
  "search_queries": [
    "Python",
    "JavaScript",
    "Java",
    "React",
    "Vue",
    "Django",
    "DevOps"
  ],
  "town": "Москва",
  "experience": null,
  "employment": null,
  "schedule": null,
  "max_pages": 5,
  "delay": 1.0,
  "universal_parsing": {
    "max_pages_per_query": 3,
    "delay": 1.0
  }
}
```

## Использование

### Основные команды

#### 1. Парсинг вакансий по текстовому запросу

```bash
# Синхронный режим
python src/manage.py parse_superjob_vacancies --text "Python" --wait

# Асинхронный режим
python src/manage.py parse_superjob_vacancies --text "Python"

# С дополнительными фильтрами
python src/manage.py parse_superjob_vacancies --text "Python" --town "Москва" --experience "between1And3" --employment "full" --wait
```

#### 2. Универсальный парсинг

```bash
# Парсинг по всем популярным запросам
python src/manage.py parse_superjob_vacancies --universal --wait

# С ограничением страниц
python src/manage.py parse_superjob_vacancies --universal --pages-per-query 2 --wait
```

#### 3. Получение деталей конкретной вакансии

```bash
# Получение деталей вакансии
python src/manage.py parse_superjob_vacancy 123456 --wait

# С сохранением в базу данных
python src/manage.py parse_superjob_vacancy 123456 --wait --save
```

### Параметры команд

#### Общие параметры:
- `--config` - путь к конфигурационному файлу (по умолчанию config.json)
- `--api-key` - API ключ SuperJob
- `--wait` - дождаться завершения задачи и вывести результат

#### Параметры поиска:
- `--text` - текст для поиска (можно указать несколько слов)
- `--town` - город для поиска
- `--experience` - уровень опыта (noExperience, between1And3, between3And6, moreThan6)
- `--employment` - тип занятости (full, part, project, volunteer, probation)
- `--schedule` - график работы (fullDay, shift, flexible, remote, flyInFlyOut)
- `--pages` - количество страниц для парсинга
- `--delay` - задержка между запросами в секундах

#### Специальные параметры:
- `--universal` - универсальный парсинг по популярным запросам
- `--pages-per-query` - количество страниц для каждого запроса
- `--use-config-only` - использовать только настройки из конфигурационного файла

## Модели данных

### SuperJobVacancy
Основная модель для хранения вакансий:
- Основная информация (название, компания, зарплата)
- Локация (город, адрес)
- Описание и требования
- Тип занятости и опыт
- Навыки и ключевые слова
- Ссылки и идентификаторы
- Метаданные и статус

### SuperJobVacancyVersion
Модель для хранения версий вакансий:
- Связь с основной вакансией
- Номер версии
- Описание изменений

### SuperJobVacancyChangeHistory
Модель для хранения истории изменений:
- Поле, которое изменилось
- Старое и новое значение
- Дата изменения

## API SuperJob

### Основные эндпоинты:
- `GET /2.0/vacancies/` - поиск вакансий
- `GET /2.0/vacancies/{id}/` - получение деталей вакансии

### Параметры поиска:
- `keyword` - ключевое слово
- `town` - город
- `experience` - опыт работы
- `employment` - тип занятости
- `schedule` - график работы
- `page` - номер страницы
- `count` - количество вакансий на странице

## Celery задачи

### Доступные задачи:
- `parse_superjob_vacancies` - парсинг вакансий по запросу
- `parse_all_superjob_vacancies` - универсальный парсинг
- `get_superjob_vacancy_details` - получение деталей вакансии
- `parse_superjob_vacancies_by_config` - парсинг по конфигурации

### Мониторинг задач:
```python
from src.modules.vacancies_parser.superjob.tasks import get_task_status

# Получение статуса задачи
status = get_task_status(task_id)
print(status)
```

## Обработка ошибок

Парсер включает в себя:
- Обработку сетевых ошибок
- Логирование всех операций
- Graceful degradation при отсутствии API ключа
- Валидацию данных перед сохранением

## Лимиты и ограничения

- Рекомендуемая задержка между запросами: 1-2 секунды
- Максимальное количество страниц на запрос: 5-10
- API SuperJob имеет ограничения на количество запросов

## Примеры использования

### 1. Парсинг IT вакансий в Москве
```bash
python src/manage.py parse_superjob_vacancies --text "Python" "JavaScript" "React" --town "Москва" --experience "between1And3" --wait
```

### 2. Универсальный парсинг с ограничениями
```bash
python src/manage.py parse_superjob_vacancies --universal --pages-per-query 2 --delay 2.0 --wait
```

### 3. Получение деталей вакансии
```bash
python src/manage.py parse_superjob_vacancy 123456 --wait --save
```

## Логирование

Все операции логируются с использованием стандартного Django logging:
- INFO - успешные операции
- WARNING - предупреждения (отсутствие API ключа и т.д.)
- ERROR - ошибки при запросах или сохранении

## Примечания

1. **API ключ**: Для полного доступа к API SuperJob необходим API ключ
2. **Лимиты**: Соблюдайте лимиты API для избежания блокировки
3. **Задержки**: Используйте задержки между запросами для корректной работы
4. **Версионность**: Система автоматически отслеживает изменения в вакансиях
5. **Асинхронность**: Используйте Celery для обработки больших объемов данных 