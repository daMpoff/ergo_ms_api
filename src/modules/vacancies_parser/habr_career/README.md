# Парсер вакансий Хабр Карьеры

Парсер для получения вакансий с платформы [Хабр Карьера](https://career.habr.com/) через их API.

## Описание

Данный модуль предоставляет функциональность для:
- Парсинга активных вакансий пользователя
- Парсинга архивных вакансий
- Получения детальной информации о вакансиях
- Сохранения данных в базу данных с версионированием
- Запуска через Django команды или Celery задачи

## Требования

Для работы парсера необходимо:
1. Зарегистрировать приложение на [Хабр Карьере](https://career.habr.com/profile/applications)
2. Получить OAuth2 токен доступа
3. Настроить права доступа к API

## Установка и настройка

### 1. Получение токена доступа

1. Перейдите на страницу [Приложения](https://career.habr.com/profile/applications)
2. Создайте новое приложение
3. Настройте OAuth2 авторизацию
4. Получите `access_token`

### 2. Настройка конфигурации

Отредактируйте файл `management/commands/config.json`:

```json
{
    "access_token": "ваш_токен_доступа",
    "pages": 5,
    "delay": 1.0,
    "get_details": true,
    "parse_archived": false,
    "parse_all": false
}
```

## Использование

### Django команды

#### Базовый парсинг активных вакансий:
```bash
python src/manage.py parse_habr_vacancies
```

#### Парсинг с кастомными параметрами:
```bash
python src/manage.py parse_habr_vacancies \
    --access-token "ваш_токен" \
    --pages 10 \
    --delay 2.0 \
    --no-details
```

#### Парсинг архивных вакансий:
```bash
python src/manage.py parse_habr_vacancies --archived
```

#### Парсинг всех вакансий (активных и архивных):
```bash
python src/manage.py parse_habr_vacancies --all
```

#### Запуск через Celery:
```bash
python src/manage.py parse_habr_vacancies --celery --wait
```

### Параметры команды

- `--access-token` - Токен доступа к API
- `--pages` - Количество страниц для парсинга
- `--delay` - Задержка между запросами в секундах
- `--no-details` - Не получать детальную информацию (быстрее)
- `--archived` - Парсить только архивные вакансии
- `--all` - Парсить все вакансии (активные и архивные)
- `--celery` - Запустить через Celery
- `--wait` - Дождаться завершения Celery задачи
- `--config` - Путь к конфигурационному файлу

### Celery задачи

```python
from src.modules.vacancies_parser.habr_career.tasks import (
    parse_habr_vacancies_task,
    parse_habr_archived_vacancies_task,
    parse_habr_all_vacancies_task
)

# Парсинг активных вакансий
task = parse_habr_vacancies_task.delay(
    access_token="ваш_токен",
    pages=5,
    delay=1.0,
    get_details=True
)

# Парсинг архивных вакансий
task = parse_habr_archived_vacancies_task.delay(
    access_token="ваш_токен",
    pages=5,
    delay=1.0
)

# Парсинг всех вакансий
task = parse_habr_all_vacancies_task.delay(
    access_token="ваш_токен",
    pages=5,
    delay=1.0,
    get_details=True
)
```

## Модели данных

### Vacancy

Основная модель для хранения вакансий:

- `title` - Название вакансии
- `company_name` - Название компании
- `salary_from/salary_to` - Зарплата от/до
- `salary_currency` - Валюта зарплаты
- `city` - Город
- `description` - Описание вакансии
- `employment_type` - Тип занятости
- `qualification` - Квалификация
- `specializations` - Специализации (JSON)
- `divisions` - Подразделения (JSON)
- `habr_id` - ID вакансии на Хабр Карьере
- `url` - Ссылка на вакансию
- `published_at` - Дата публикации
- `is_active` - Активна ли вакансия

### VacancyVersion

Модель для хранения версий вакансий:

- `vacancy` - Связь с вакансией
- `version_number` - Номер версии
- `created_at` - Дата создания версии
- `change_summary` - Описание изменений

### VacancyChangeHistory

Модель для хранения истории изменений:

- `vacancy` - Связь с вакансией
- `version` - Связь с версией
- `field_name` - Название измененного поля
- `old_value/new_value` - Старое/новое значение

## API методы

### HabrCareerParser

Основной класс для работы с API:

- `get_vacancies(page, per_page)` - Получение активных вакансий
- `get_archived_vacancies(page, per_page)` - Получение архивных вакансий
- `get_vacancy_details(vacancy_id)` - Получение деталей вакансии
- `get_user_info()` - Получение информации о пользователе
- `parse_vacancy(vacancy_data)` - Парсинг данных вакансии
- `save_vacancy(vacancy_data)` - Сохранение вакансии в БД

## Функции парсинга

- `parse_habr_vacancies(access_token, pages, delay, get_details)` - Парсинг активных вакансий
- `parse_habr_archived_vacancies(access_token, pages, delay)` - Парсинг архивных вакансий

## Особенности

1. **Версионирование**: Все изменения вакансий сохраняются с версиями
2. **Детальный парсинг**: Возможность получения полной информации о вакансиях
3. **Обработка ошибок**: Корректная обработка ошибок API
4. **Задержки**: Настраиваемые задержки между запросами
5. **Celery интеграция**: Поддержка асинхронного выполнения
6. **Конфигурация**: Гибкая настройка через JSON файлы

## Ограничения API

Согласно [документации API Хабр Карьеры](https://career.habr.com/info/api):

- API работает по протоколу HTTPS
- Авторизация через OAuth2
- Данные доступны только в формате JSON
- Токены доступа перманентны
- Нет ограничений на объем данных

## Примеры использования

### Простой парсинг
```bash
# Парсинг 5 страниц активных вакансий
python src/manage.py parse_habr_vacancies --access-token "токен"
```

### Парсинг с деталями
```bash
# Парсинг с получением детальной информации
python src/manage.py parse_habr_vacancies \
    --access-token "токен" \
    --pages 10 \
    --delay 2.0
```

### Парсинг через Celery
```bash
# Асинхронный парсинг
python src/manage.py parse_habr_vacancies \
    --access-token "токен" \
    --celery \
    --wait
```

### Парсинг всех вакансий
```bash
# Активные и архивные вакансии
python src/manage.py parse_habr_vacancies \
    --access-token "токен" \
    --all \
    --pages 3
``` 