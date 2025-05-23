# Конфигурация Django проекта

Документация по конфигурации Django проекта. 
Конфигурация организована модульным способом для лучшей поддерживаемости.

## Структура конфигурации
```
src/config/
├── patterns/                  # Паттерны настроек для разных окружений
|   ├── __init__.py           # Инициализация пакета
│   ├── base.py               # Базовые URL паттерны
│   ├── development.py        # Настройки для разработки
│   ├── local.py              # Агрегатор локальных настроек
│   └── production.py         # Настройки для продакшена
|
├── settings/                 # Модули настроек по категориям
|   ├── __init__.py          # Инициализация пакета
│   ├── apps.py              # Приложения и middleware
│   ├── auth.py              # Аутентификация и авторизация
│   ├── auto_api.py          # Настройки автогенерации API
│   ├── base.py              # Базовые настройки и пути
│   ├── celery.py            # Настройки Celery и SQLite
│   ├── cors.py              # Настройки CORS
│   ├── database.py          # Конфигурация БД
│   ├── localization.py      # Локализация
│   ├── logger.py            # Логирование
│   ├── server.py            # Настройки сервера
│   ├── smtp.py              # Настройки почты
│   ├── static.py            # Статические файлы
│   ├── swagger.py           # Настройки Swagger
│   └── templates.py         # Шаблоны и WSGI/ASGI
|
├── __init__.py              # Инициализация пакета
├── asgi.py                  # Конфигурация ASGI
├── auto_api.yaml            # Конфигурация автогенерации API
├── celery.py                # Конфигурация Celery
├── env.py                   # Обработчик переменных окружения
├── urls.py                  # Основные URL
├── wsgi.py                  # Конфигурация WSGI
└── yasg.py                  # Настройки Swagger
```

## Основные компоненты

### Базовые настройки

- Определение основных путей системы (`settings/base.py`):
  - `BASE_DIR`: Корневая директория проекта
  - `SYSTEM_DIR`: Корневая директория системы

- Определение основных путей системы (`settings/static.py`):
  - `EXTERNAL_MODULES_DIR`: Директория внешних модулей
  - `RESOURCES_DIR`: Директория ресурсов
  - `LOGS_DIR`: Директория логов

### Паттерны окружения

- **Настройки разработки** (`patterns/development.py`): Конфигурация для среды разработки
- **Настройки продакшена** (`patterns/production.py`): Конфигурация для продакшен-среды
- **Локальные настройки** (`patterns/local.py`): Объединяет все файлы настроек
- **Базовые URL паттерны** (`patterns/base.py`): Базовые URL паттерны для Django

### Основные настройки

1. **Приложения** (`settings/apps.py`)
   - Автоматическое обнаружение приложений из основных и внешних модулей
   - Конфигурация встроенных приложений Django
   - Настройка middleware
   - Управление порядком загрузки приложений

2. **Аутентификация** (`settings/auth.py`)
   - Валидация паролей
   - Настройки JWT аутентификации
   - Ограничение частоты запросов
   - Настройки безопасности Swagger
   - Конфигурация CORS

3. **База данных** (`settings/database.py`)
   - Поддержка множественных подключений к разным типам СУБД
   - Конфигурация через YAML файл
   - Автоматическое переключение на SQLite при ошибках подключения
   - Поддержка PostgreSQL, MySQL, SQLite и MSSQL
   - Настройки SSH туннелирования
   - Обработка ошибок подключения
   - Тестирование подключений при старте

4. **Статические файлы** (`settings/static.py`)
   - Конфигурация статических файлов
   - Настройки медиа файлов
   - Настройка директории для логов и ресурсов
   - Конфигурация Whitenoise
   - Определение путей к ресурсам

5. **Локализация** (`settings/localization.py`)
   - Языковые настройки
   - Конфигурация временных зон
   - Параметры интернационализации
   - Форматы дат и чисел

6. **Celery и SQLite** (`settings/celery.py`)
   - Настройки брокера сообщений SQLite
   - Конфигурация сериализации задач
   - Настройки временной зоны
   - Путь к SQLite серверу
   - Настройки повторных попыток

7. **Логирование** (`settings/logger.py`)
   - Конфигурация форматтеров
   - Настройка обработчиков
   - Уровни логирования
   - Ротация логов
   - Специфичные логгеры для разных компонентов

8. **Шаблоны** (`settings/templates.py`)
   - Настройка движков шаблонов
   - Пути к шаблонам
   - Контекстные процессоры
   - Настройки кэширования

9. **SMTP** (`settings/smtp.py`)
   - Настройки SMTP сервера
   - Параметры электронной почты
   - Настройки безопасности

10. **Серверные настройки** (`settings/server.py`)  
    - Настройки серверного процесса
    - Параметры сервера
    - Настройки безопасности

11. **Swagger** (`settings/swagger.py`)
    - Настройки Swagger
    - Параметры Swagger

12. **CORS** (`settings/cors.py`)
    - Настройки CORS
    - Параметры CORS
    - Настройки безопасности

13. **Аутентификация** (`settings/auth.py`)
    - Настройки аутентификации
    - Параметры аутентификации
    - Настройки безопасности

14. **Генерация API** (`settings/auto_api.py`)
    - Настройки автоматической генерации API
    - Параметры автоматической генерации API
    - Настройки безопасности

### Серверная конфигурация

- **ASGI** (`asgi.py`): Настройка асинхронного серверного шлюза
- **WSGI** (`wsgi.py`): Настройка веб-серверного шлюза

### Документация API

- **Swagger/OpenAPI** (`yasg.py`): Настройка документации API с точками доступа:
  - `/swagger.json` или `/swagger.yaml` для схемы
  - `/swagger/` для Swagger UI
  - `/redoc/` для ReDoc интерфейса

## Конфигурационные файлы

### Переменные окружения (ergo_ms/.env)

- **Обработка переменных окружения** (`env.py`): Обработчик переменных окружения

Основные переменные окружения включают:

```
# Общие настройки системы
SYSTEM_TITLE=ERGO MS      # Название системы   

# Настройки API
API_HOST=localhost        # Хост для API сервера
API_PORT=8000            # Порт API сервера
API_ALLOWED_HOSTS=localhost,127.0.0.1  # Разрешенные хосты
API_DEPLOY_TYPE=development  # Тип развертывания (development/production)

# Настройки токенов
API_ACCESS_TOKEN_LIFETIME=30    # Время жизни access токена (в минутах)
API_REFRESH_TOKEN_LIFETIME=1440 # Время жизни refresh токена (в минутах, 1440 = 1 день)

# Ограничения запросов
API_THROTTLE_RATES_ANON=10/minute  # Лимит запросов для анонимных пользователей
API_THROTTLE_RATES_USER=5000/hour  # Лимит запросов для авторизованных пользователей

# Безопасность
API_SECRET_KEY=secret-key  # Секретный ключ (замените на сложный случайный ключ)
```

### Конфигурация баз данных (ergo_ms/databases.yaml)

Пример конфигурации для разных типов СУБД:

```yaml
databases:

  default:
    engine: postgresql
    name: db_name
    user: db_user
    password: db_password
    host: localhost
    port: 5432
    ssh:  # Опционально
      host: ssh_host
      port: 22
      username: ssh_user
      password: ssh_password
      key_path: path/to/key

  secondary:
    engine: mysql
    name: mysql_db
    user: mysql_user
    password: mysql_pass
    host: localhost
    port: 3306
```

### Настройка API методов для автоматической генерации (auto_api.yaml)

Настройка генерации API методов:

```yaml
MessagesView:
  path: test-integration/messages/
  method: GET
  handler: messages.messages_handler
  status_code: 200
  renderers: json, browsable
  auth_required: false
  throttle_rates:
    anon: 1/minute
    user: 1/minute
  required_params: []
  optional_params:
    type: info
  description: >
    Получение различных типов системных сообщений.

    Доступные типы сообщений:
    - info: Информационные сообщения
    - error: Сообщения об ошибках
    - warning: Предупреждения
    - success: Сообщения об успешных операциях
  params_description:
    type:
      description: Тип запрашиваемого сообщения (по умолчанию - info)
      type: string
  responses:
    200:
      description: Сообщение успешно получено
      example:
        message:
          title: Информационное сообщение
          text: Это информационное сообщение для пользователя
          level: info
    400:
      description: Неверный тип сообщения
      example:
        error: "Указан неподдерживаемый тип сообщения"
```

## Логирование

Конфигурация логирования (`settings/logger.py`) обеспечивает:
- Логирование в файлы в директории `logs/`
- Вывод в консоль
- Различные форматтеры для разных нужд логирования
- Отдельные логгеры для Django и стандартных функций
- Ротацию логов по размеру и времени
- Специальные обработчики для разных окружений

## Примечания по безопасности

- JWT аутентификация настроена с настраиваемым временем жизни токенов
- Реализовано ограничение частоты запросов
- Настроен CORS middleware для реализации кросс-доменных запросов
- Включена безопасная валидация паролей
- Режим отладки отключен в продакшен-настройках
- Поддержка SSL/TLS для баз данных
- Возможность SSH туннелирование для безопасного подключения к БД
- Безопасное хранение секретов в скрытых конфигурационных файлах
- Защита от CSRF атак
- Настроенные заголовки безопасности