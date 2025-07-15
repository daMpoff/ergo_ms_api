# Система команд Poetry для Django

Автоматическое создание poetry команд для всех Django команд (встроенных и пользовательских).
Реализовано для упрощения синтаксиса обращения к Django командам.

## Использование

### Базовые команды
```bash
# Запуск сервера разработки
cmd dev

# Создание миграций
cmd makemigrations

# Применение миграций
cmd migrate

# Пользовательские команды
cmd clear_cache
cmd clear_pycache
```

### Альтернативный синтаксис
```bash
# Можно использовать poetry run
poetry run cmd runserver

# Или просто cmd
cmd runserver
```

## Создание пользовательской команды

1. Создайте файл в папке `management/commands/` вашего приложения:

```python
# src/modules/myapp/management/commands/my_command.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Описание команды'

    def add_arguments(self, parser):
        parser.add_argument('--option', type=str, help='Опция')

    def handle(self, *args, **options):
        self.stdout.write('Команда выполнена!')
```

2. Команда автоматически станет доступной:
```bash
cmd my_command --option value
```

## Конфигурация

### pyproject.toml
```toml
[tool.poetry.scripts]
cmd = "commands.__main__:main"
```

## Просмотр всех команд

```bash
cmd
```