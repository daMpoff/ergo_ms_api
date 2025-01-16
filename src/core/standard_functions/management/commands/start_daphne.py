"""
Файл для определения команды Django для управления сервером Daphne (запуск).

Этот файл содержит класс `Command`, который наследуется от `BaseCommand` и предоставляет команду для запуска
сервера Daphne. Команда позволяет указать уровень логирования и запускает сервер Daphne с использованием класса `Daphne`.
После запуска сервера команда проверяет, работает ли процесс сервера, и выводит соответствующее сообщение.

Класс `Command`:
- `help` (str): Краткое описание команды, которое будет отображаться в справке Django.
- `add_arguments(self, parser)`: Метод, который добавляет аргументы командной строки для команды. В данном случае,
  добавляется аргумент `--log-level` для указания уровня логирования.
- `handle(self, *args, **options)`: Метод, который выполняет основную логику команды. В данном случае, он запускает
  сервер Daphne с указанным уровнем логирования и проверяет, работает ли процесс сервера.

Пример использования:
Для запуска сервера с уровнем логирования по умолчанию (info):
>>> python src/manage.py start_daphne

Для запуска сервера с указанным уровнем логирования (например, warning):
>>> python src/manage.py start_daphne --log-level warning
"""

from django.core.management.base import BaseCommand
from src.core.standard_functions.enums import LogLevel
from src.core.standard_functions.daphne import Daphne

class Command(BaseCommand):
    """
    Команда Django для управления сервером Daphne (запуск).

    Этот класс наследуется от `BaseCommand` и предоставляет команду для запуска сервера Daphne. Команда позволяет
    указать уровень логирования и запускает сервер Daphne с использованием класса `Daphne`. После запуска сервера
    команда проверяет, работает ли процесс сервера, и выводит соответствующее сообщение.

    Атрибуты:
        help (str): Краткое описание команды, которое будет отображаться в справке Django.

    Методы:
        add_arguments(self, parser): Метод, который добавляет аргументы командной строки для команды. В данном случае,
                                     добавляется аргумент `--log-level` для указания уровня логирования.
        handle(self, *args, **options): Метод, который выполняет основную логику команды. В данном случае, он запускает
                                        сервер Daphne с указанным уровнем логирования и проверяет, работает ли процесс
                                        сервера.
    """
    help = "Управление сервером Daphne (запуск)"

    def add_arguments(self, parser):
        """
        Добавляет аргументы командной строки для команды.

        В данном случае, добавляется аргумент `--log-level` для указания уровня логирования.

        Аргументы:
            parser: Объект парсера аргументов командной строки.
        """
        parser.add_argument(
            '--log-level',
            type=str,
            choices=[level.value for level in LogLevel],
            default=LogLevel.INFO.value,
            help='Уровень логирования (info, warning, error, none)'
        )

    def handle(self, *args, **options):
        """
        Выполняет основную логику команды.

        Запускает сервер Daphne с указанным уровнем логирования и проверяет, работает ли процесс сервера.

        Аргументы:
            *args: Дополнительные аргументы, переданные в команду.
            **options: Дополнительные именованные аргументы, переданные в команду.
        """
        log_level = LogLevel(options['log_level'])
        daphne = Daphne()
        process = daphne.start_daphne(log_level)

        is_process_running = daphne.is_process_running(process)

        if is_process_running:
            self.stdout.write(self.style.SUCCESS('Сервер успешно запущен.'))
        else:
            self.stdout.write(self.style.ERROR('Не удалось запустить сервер.'))