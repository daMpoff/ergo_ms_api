"""
Django команда: клонирует (или обновляет) репозиторий snakers4/silero-models в packages,
чтобы torch.hub мог загружать модели из локального пути без cache в профиле.
"""

import os
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from src.config.settings.static import PACKAGES_PATH


class Command(BaseCommand):
    help = 'Устанавливает локальный репозиторий Silero в packages/silero-models'

    def handle(self, *args, **options):
        packages_dir = Path(PACKAGES_PATH)
        repo_dir = packages_dir / 'silero-models'
        repo_url = 'https://github.com/snakers4/silero-models.git'

        packages_dir.mkdir(parents=True, exist_ok=True)

        if repo_dir.exists():
            self.stdout.write('Репозиторий уже существует, выполняю git pull...')
            try:
                subprocess.run(['git', '-C', str(repo_dir), 'pull', '--ff-only'], check=True)
                self.stdout.write(self.style.SUCCESS('Обновление завершено'))
            except Exception as e:
                raise CommandError(f'Не удалось обновить репозиторий: {e}')
        else:
            self.stdout.write(f'Клонирую {repo_url} в {repo_dir}...')
            try:
                subprocess.run(['git', 'clone', '--depth', '1', repo_url, str(repo_dir)], check=True)
                self.stdout.write(self.style.SUCCESS('Клонирование завершено'))
            except Exception as e:
                raise CommandError(f'Не удалось клонировать репозиторий: {e}')

        # Быстрая проверка наличия hubconf.py и src/silero
        hubconf = repo_dir / 'hubconf.py'
        src_dir = repo_dir / 'src' / 'silero'
        if not hubconf.exists() or not src_dir.exists():
            raise CommandError('Репозиторий Silero не содержит ожидаемых файлов (hubconf.py, src/silero)')

        self.stdout.write(self.style.SUCCESS('Локальный репозиторий Silero готов'))

