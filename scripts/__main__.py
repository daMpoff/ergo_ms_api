"""
Файл для связи poetry и команд созданных в commands.py.

Данный функционал взаимодействует с Poetry при помощи следующей секции pyproject.toml файла:

[tool.poetry.scripts]
cmd = "scripts.__main__:main"

Пример команды для запуска сервера Django API:
>>> poetry run cmd dev
"""

import sys
import inspect
import logging

from scripts.commands import PoetryCommand
from src.config.settings.logger import LOGGING

# Настройка логгера для скриптов
logger = logging.getLogger('scripts')

# Использование форматтера из конфигурации
formatter = logging.Formatter(
    fmt=LOGGING['formatters']['simple']['format'],
    style=LOGGING['formatters']['simple']['style']
)

# Настройка вывода только в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

def main():
    """
    Точка входа для управления командами через Poetry.

    Этот скрипт динамически загружает все доступные команды, которые являются подклассами `PoetryCommand`,
    и предоставляет интерфейс для их вызова через терминал.

    Основные этапы выполнения:
    1. Загрузка всех команд из модуля `scripts.commands`.
    2. Проверка переданных аргументов.
    3. Поиск команды по её имени (ключ `poetry_command_name`).
    4. Выполнение команды с переданными аргументами.

    Пример использования:
        В терминале, запустите:
        ```bash
        poetry run <команда> [аргументы...]
        ```

        Например:
        ```bash
        poetry run cmd makemigrations --dry-run
        poetry run cmd dev
        poetry run cmd collectstatic --no-input
        ```

    Вывод:
        Если команды отсутствуют или указана неверная команда, будет выведен список доступных команд.

    Исключения:
        - Выход с кодом `1`, если команда не указана.
        - Выход с кодом `1`, если указана неизвестная команда.

    Зависимости:
        - Модуль `scripts.commands` должен содержать классы команд, наследующие `PoetryCommand`.
    """
    # Динамически получаем все классы, наследующие PoetryCommand
    modules = sys.modules["scripts.commands"]

    # Создаем словарь команд
    commands = {}

    # Ищем все классы, наследующие PoetryCommand, но не сам PoetryCommand
    for _, cls in inspect.getmembers(modules, inspect.isclass):
        if issubclass(cls, PoetryCommand) and cls is not PoetryCommand:
            # Добавляем класс в словарь с ключом, равным poetry_command_name
            commands[cls.poetry_command_name] = cls

    # Проверяем, что указана команда
    if len(sys.argv) < 2:
        logger.info("Использование: poetry run <команда> [аргументы...]")
        logger.info("Доступные команды: %s", ", ".join(commands.keys()))
        return

    # Получаем имя команды и аргументы
    command_name = sys.argv[1]
    args = sys.argv[2:]

    # Проверяем, существует ли команда
    CommandClass = commands.get(command_name)
    if not CommandClass:
        logger.error("Неизвестная команда: %s", command_name)
        logger.info("Доступные команды: %s", ", ".join(commands.keys()))
        return

    # Создаём экземпляр команды и вызываем метод run
    CommandClass().run(*args)

if __name__ == "__main__":
    main()