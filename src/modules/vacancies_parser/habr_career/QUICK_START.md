# Быстрый старт - Парсер Хабр Карьеры

## 1. Получение токена доступа

1. Перейдите на [Хабр Карьера - Приложения](https://career.habr.com/profile/applications)
2. Создайте новое приложение
3. Настройте OAuth2 авторизацию
4. Скопируйте `access_token`

## 2. Настройка конфигурации

Отредактируйте файл `management/commands/config.json`:

```json
{
    "access_token": "ваш_токен_доступа_здесь",
    "pages": 5,
    "delay": 1.0,
    "get_details": true,
    "parse_archived": false,
    "parse_all": false
}
```

## 3. Запуск парсинга

### Базовый запуск:
```bash
python src/manage.py parse_habr_vacancies
```

### С кастомными параметрами:
```bash
python src/manage.py parse_habr_vacancies \
    --access-token "ваш_токен" \
    --pages 10 \
    --delay 2.0
```

### Парсинг архивных вакансий:
```bash
python src/manage.py parse_habr_vacancies --archived
```

### Парсинг всех вакансий:
```bash
python src/manage.py parse_habr_vacancies --all
```

### Через Celery:
```bash
python src/manage.py parse_habr_vacancies --celery --wait
```

## 4. Проверка результатов

После выполнения команды вы увидите статистику:
- Всего обработано вакансий
- Новых вакансий
- Обновлено вакансий
- Количество ошибок

## 5. Полезные параметры

- `--access-token` - Токен доступа (обязательно)
- `--pages` - Количество страниц (по умолчанию 5)
- `--delay` - Задержка между запросами в секундах (по умолчанию 1.0)
- `--no-details` - Быстрый парсинг без деталей
- `--archived` - Только архивные вакансии
- `--all` - Все вакансии (активные + архивные)
- `--celery` - Запуск через Celery
- `--wait` - Дождаться завершения Celery задачи

## Примеры использования

```bash
# Простой парсинг 5 страниц
python src/manage.py parse_habr_vacancies --access-token "токен"

# Парсинг 10 страниц с задержкой 2 секунды
python src/manage.py parse_habr_vacancies \
    --access-token "токен" \
    --pages 10 \
    --delay 2.0

# Быстрый парсинг без деталей
python src/manage.py parse_habr_vacancies \
    --access-token "токен" \
    --no-details

# Парсинг всех вакансий через Celery
python src/manage.py parse_habr_vacancies \
    --access-token "токен" \
    --all \
    --celery \
    --wait
``` 