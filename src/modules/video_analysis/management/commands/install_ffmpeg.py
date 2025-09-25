"""
Django команда для установки ffmpeg в папку packages/ffmpeg/.
"""

import os
import subprocess
import sys
import zipfile
import tarfile
import requests
import shutil
import platform
from pathlib import Path

from src.config.settings.static import PACKAGES_PATH

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Команда для установки ffmpeg."""
    
    help = 'Устанавливает ffmpeg в папку packages/ffmpeg/'
    
    def add_arguments(self, parser):
        """Добавляет аргументы команды."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно переустановить ffmpeg, даже если он уже установлен',
        )
        parser.add_argument(
            '--ffmpeg-version',
            type=str,
            default='6.1.1',
            help='Версия ffmpeg для установки (по умолчанию: 6.1.1)',
        )
    
    def handle(self, *args, **options):
        """Выполнение команды."""
        try:
            # Определяем пути
            ffmpeg_dir = Path(PACKAGES_PATH) / "ffmpeg"
            temp_dir = Path(PACKAGES_PATH) / "temp_ffmpeg"
            
            self.stdout.write("🚀 Начинаю установку ffmpeg...")
            
            # Проверяем, не установлен ли уже ffmpeg
            if self._is_ffmpeg_installed(ffmpeg_dir) and not options['force']:
                self.stdout.write(
                    self.style.SUCCESS("✅ ffmpeg уже установлен в packages/ffmpeg/")
                )
                self.stdout.write(f"📁 Путь: {ffmpeg_dir.absolute()}")
                return
            
            if options['force']:
                self.stdout.write("🔄 Принудительная переустановка ffmpeg...")
            
            # Создаем временную папку
            temp_dir.mkdir(exist_ok=True)
            
            # Определяем версию ffmpeg и URL в зависимости от ОС
            ffmpeg_version = options['ffmpeg_version']
            ffmpeg_url = self._get_ffmpeg_url()
            
            self.stdout.write(f"📥 Загружаю ffmpeg версии {ffmpeg_version}...")
            
            # Загружаем ffmpeg
            archive_path = self._download_ffmpeg(ffmpeg_url, temp_dir)
            if not archive_path:
                raise CommandError("Не удалось загрузить ffmpeg")
            
            self.stdout.write("📦 Распаковываю архив...")
            
            # Распаковываем архив
            if not self._extract_ffmpeg(archive_path, temp_dir, ffmpeg_dir):
                raise CommandError("Не удалось распаковать архив ffmpeg")
            
            self.stdout.write("🔧 Настраиваю структуру папок...")
            
            # Настраиваем структуру папок
            if not self._setup_ffmpeg_structure(ffmpeg_dir):
                raise CommandError("Не удалось настроить структуру папок ffmpeg")
            
            self.stdout.write("🧹 Очищаю временные файлы...")
            
            # Очищаем временные файлы
            self._cleanup(temp_dir)
            
            self.stdout.write(
                self.style.SUCCESS("✅ ffmpeg успешно установлен в packages/ffmpeg/")
            )
            self.stdout.write(f"📁 Путь: {ffmpeg_dir.absolute()}")
            
        except Exception as e:
            self._cleanup(temp_dir)
            raise CommandError(f"Ошибка при установке ffmpeg: {e}")
    
    def _is_ffmpeg_installed(self, ffmpeg_dir: Path) -> bool:
        """Проверяет, установлен ли уже ffmpeg."""
        system = platform.system().lower()
        if system == "windows":
            ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg.exe"
        else:
            ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg"
        return ffmpeg_exe.exists()
    
    def _download_ffmpeg(self, url: str, temp_dir: Path) -> Path:
        """Загружает архив ffmpeg."""
        try:
            # Определяем расширение файла по URL
            if url.endswith('.tar.xz'):
                archive_path = temp_dir / "ffmpeg.tar.xz"
            else:
                archive_path = temp_dir / "ffmpeg.zip"
            
            self.stdout.write(f"📥 Загружаю {url}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.stdout.write(f"\r📥 Прогресс: {progress:.1f}%", ending='')
                            self.stdout.flush()
            
            self.stdout.write()  # Новая строка после прогресса
            return archive_path
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при загрузке ffmpeg: {e}")
            )
            return None
    
    def _extract_ffmpeg(self, archive_path: Path, temp_dir: Path, ffmpeg_dir: Path) -> bool:
        """Распаковывает архив ffmpeg."""
        try:
            if archive_path.suffix == '.xz' or str(archive_path).endswith('.tar.xz'):
                # Распаковываем tar.xz архив
                with tarfile.open(archive_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(temp_dir)
            else:
                # Распаковываем zip архив
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            
            # Ищем папку с распакованным ffmpeg
            extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name.startswith('ffmpeg')]
            if not extracted_dirs:
                self.stdout.write(
                    self.style.ERROR("❌ Не удалось найти распакованную папку ffmpeg")
                )
                return False
            
            # Перемещаем содержимое в целевую папку
            source_dir = extracted_dirs[0]
            if ffmpeg_dir.exists():
                shutil.rmtree(ffmpeg_dir)
            
            shutil.move(str(source_dir), str(ffmpeg_dir))
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при распаковке ffmpeg: {e}")
            )
            return False
    
    def _setup_ffmpeg_structure(self, ffmpeg_dir: Path) -> bool:
        """Настраивает структуру папок ffmpeg."""
        try:
            system = platform.system().lower()
            
            # Проверяем, что основные файлы на месте
            if system == "windows":
                ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg.exe"
                ffprobe_exe = ffmpeg_dir / "bin" / "ffprobe.exe"
            else:
                ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg"
                ffprobe_exe = ffmpeg_dir / "bin" / "ffprobe"
                
                # На Linux делаем файлы исполняемыми
                if ffmpeg_exe.exists():
                    os.chmod(ffmpeg_exe, 0o755)
                if ffprobe_exe.exists():
                    os.chmod(ffprobe_exe, 0o755)
            
            if not ffmpeg_exe.exists() or not ffprobe_exe.exists():
                self.stdout.write(
                    self.style.ERROR("❌ Не найдены основные исполняемые файлы ffmpeg")
                )
                return False
            
            # Проверяем работоспособность
            result = subprocess.run(
                [str(ffmpeg_exe), "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.stdout.write(
                    self.style.ERROR("❌ ffmpeg не работает корректно")
                )
                return False
            
            version_info = "неизвестна"
            if 'ffmpeg version' in result.stdout:
                version_info = result.stdout.split('ffmpeg version')[1].split()[0]
            
            self.stdout.write(f"✅ Версия ffmpeg: {version_info}")
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при настройке структуры: {e}")
            )
            return False
    
    def _get_ffmpeg_url(self) -> str:
        """Возвращает URL для загрузки ffmpeg в зависимости от ОС."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        elif system == "linux":
            if machine in ["x86_64", "amd64"]:
                return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
            elif machine in ["aarch64", "arm64"]:
                return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz"
            else:
                raise CommandError(f"Неподдерживаемая архитектура Linux: {machine}")
        elif system == "darwin":  # macOS
            if machine in ["x86_64", "amd64"]:
                return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.zip"
            elif machine in ["arm64"]:
                return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macosarm64-gpl.zip"
            else:
                raise CommandError(f"Неподдерживаемая архитектура macOS: {machine}")
        else:
            raise CommandError(f"Неподдерживаемая операционная система: {system}")
    
    def _cleanup(self, temp_dir: Path):
        """Очищает временные файлы."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️ Предупреждение: не удалось очистить временные файлы: {e}")
            )
