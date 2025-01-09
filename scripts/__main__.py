import sys
import inspect

from scripts.commands import PoetryCommand

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
        poetry run makemigrations --dry-run
        poetry run dev
        poetry run collectstatic --no-input
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
        print("Использование: poetry run <команда> [аргументы...]")
        print("Доступные команды:", ", ".join(commands.keys()))
        sys.exit(1)

    # Получаем имя команды и аргументы
    command_name = sys.argv[1]
    args = sys.argv[2:]

    # Проверяем, существует ли команда
    CommandClass = commands.get(command_name)
    if not CommandClass:
        print(f"Неизвестная команда: {command_name}")
        print("Доступные команды:", ", ".join(commands.keys()))
        sys.exit(1)

    # Создаём экземпляр команды и вызываем метод run
    CommandClass().run(*args)

if __name__ == "__main__":
    main()