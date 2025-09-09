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

        # Перезаписываем hubconf.py требуемым содержимым
        try:
            desired_hubconf = (
                "dependencies = [\"torch\"]\n\n"
                "import sys\n"
                "from silero import (\n"
                "    silero_stt,\n"
                "    silero_tts,\n"
                "    silero_te,\n"
                ")\n\n"
                "__all__ = [\n"
                "    \"silero_stt\",\n"
                "    \"silero_tts\",\n"
                "    \"silero_te\",\n"
                "]\n\n"
                "sys.path.append(\"src/silero\")\n"
            )
            hubconf.write_text(desired_hubconf, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS('hubconf.py обновлён по требованиям проекта'))
        except Exception as e:
            raise CommandError(f'Не удалось обновить hubconf.py: {e}')

        self.stdout.write(self.style.SUCCESS('Локальный репозиторий Silero готов'))