from django.core.management.commands.runserver import Command as RunserverCommand

from src.config.settings.server import SERVER_PORT, SERVER_HOST

# Переопределение команды runserver
class Command(RunserverCommand):
    # Переопределяем метод add_arguments для добавления аргументов командной строки
    def add_arguments(self, parser):
        super().add_arguments(parser)

    # Переопределяем метод handle для обработки команды
    def handle(self, *args, **options):
        # Проверяем, установлен ли аргумент addrport (адрес и порт)
        if not options['addrport']:
            # Если аргумент addrport не установлен, устанавливаем его по умолчанию
            # Используем значения SERVER_HOST и SERVER_PORT из конфигурационного файла
            options['addrport'] = f'{SERVER_HOST}:{SERVER_PORT}'  # Хост и порт по умолчанию

        # Вызываем метод handle родительского класса для выполнения стандартной обработки команды
        super().handle(*args, **options)