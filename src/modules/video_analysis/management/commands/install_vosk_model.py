"""
Django команда для установки vosk-model-ru в папку trained_models/.
"""

import os
import subprocess
import sys
import zipfile
import requests
import shutil
from pathlib import Path

from src.config.settings.static import TRAINED_MODELS_PATH

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Команда для установки vosk-model-ru."""
    
    help = 'Устанавливает vosk-model-ru в папку trained_models/'
    
    def add_arguments(self, parser):
        """Добавляет аргументы команды."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно переустановить vosk-model-ru, даже если он уже установлен',
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default='vosk-model-ru-0.42',
            help='Название модели для установки (по умолчанию: vosk-model-ru-0.42)',
        )
    
    def handle(self, *args, **options):
        """Выполнение команды."""
        try:
            # Определяем пути
            model_name = options['model_version']
            model_dir = Path(TRAINED_MODELS_PATH) / model_name
            temp_dir = Path(TRAINED_MODELS_PATH) / "temp_vosk_model"
            
            self.stdout.write("🚀 Начинаю установку vosk-model-ru...")
            
            # Проверяем, не установлен ли уже vosk-model-ru
            if self._is_model_installed(model_dir) and not options['force']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {model_name} уже установлен в trained_models/{model_name}/")
                )
                self.stdout.write(f"📁 Путь: {model_dir.absolute()}")
                return
            
            if options['force']:
                self.stdout.write("🔄 Принудительная переустановка vosk-model-ru...")
            
            # Создаем временную папку
            temp_dir.mkdir(exist_ok=True)
            
            self.stdout.write(f"📥 Загружаю {model_name}...")
            
            # Загружаем архив модели
            if not self._download_model_archive(model_name, temp_dir):
                raise CommandError("Не удалось загрузить архив модели")
            
            self.stdout.write("📦 Распаковываю архив...")
            
            # Распаковываем архив
            if not self._extract_model_archive(temp_dir, model_dir):
                raise CommandError("Не удалось распаковать архив модели")
            
            self.stdout.write("🔧 Проверяю работоспособность модели...")
            
            # Проверяем работоспособность
            if not self._verify_model(model_dir):
                raise CommandError("Модель не работает корректно")
            
            self.stdout.write("🧹 Очищаю временные файлы...")
            
            # Очищаем временные файлы
            self._cleanup(temp_dir)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ {model_name} успешно установлен в trained_models/{model_name}/")
            )
            self.stdout.write(f"📁 Путь: {model_dir.absolute()}")
            
        except Exception as e:
            self._cleanup(temp_dir)
            raise CommandError(f"Ошибка при установке vosk-model-ru: {e}")
    
    def _is_model_installed(self, model_dir: Path) -> bool:
        """Проверяет, установлен ли уже vosk-model-ru."""
        # Проверяем наличие основных папок и файлов модели
        required_dirs = ['am', 'graph', 'conf', 'ivector']
        required_files = ['README', 'decode.py']
        
        # Проверяем папки
        for dir_name in required_dirs:
            if not (model_dir / dir_name).exists():
                return False
        
        # Проверяем файлы
        for file_name in required_files:
            if not (model_dir / file_name).exists():
                return False
        
        return True
    
    def _download_model_archive(self, model_name: str, temp_dir: Path) -> bool:
        """Загружает архив модели vosk."""
        try:
            # URL для загрузки vosk-model-ru-0.42
            model_url = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
            
            self.stdout.write(f"📥 Загружаю архив с {model_url}...")
            
            response = requests.get(model_url, stream=True)
            response.raise_for_status()
            
            zip_path = temp_dir / f"{model_name}.zip"
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.stdout.write(f"\r📥 Прогресс: {progress:.1f}%", ending='')
                            self.stdout.flush()
            
            self.stdout.write()  # Новая строка после прогресса
            
            # Проверяем размер загруженного файла
            file_size_mb = zip_path.stat().st_size / (1024 * 1024)
            self.stdout.write(f"📦 Размер архива: {file_size_mb:.1f} MB")
            
            if file_size_mb < 100:  # Архив должен быть больше 100MB
                self.stdout.write(
                    self.style.WARNING("⚠️ Размер архива меньше ожидаемого")
                )
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при загрузке архива модели: {e}")
            )
            return False
    
    def _extract_model_archive(self, temp_dir: Path, model_dir: Path) -> bool:
        """Распаковывает архив модели."""
        try:
            # Ищем zip файл
            zip_files = list(temp_dir.glob("*.zip"))
            if not zip_files:
                self.stdout.write(
                    self.style.ERROR("❌ Не найден архив для распаковки")
                )
                return False
            
            zip_path = zip_files[0]
            self.stdout.write(f"📦 Распаковываю {zip_path.name}...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Ищем папку с распакованной моделью
            extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name.startswith('vosk-model-ru')]
            if not extracted_dirs:
                self.stdout.write(
                    self.style.ERROR("❌ Не удалось найти распакованную папку vosk-model-ru")
                )
                return False
            
            # Перемещаем содержимое в целевую папку
            source_dir = extracted_dirs[0]
            if model_dir.exists():
                shutil.rmtree(model_dir)
            
            shutil.move(str(source_dir), str(model_dir))
            
            self.stdout.write("✅ Архив успешно распакован")
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при распаковке архива: {e}")
            )
            return False
    
    def _verify_model(self, model_dir: Path) -> bool:
        """Проверяет работоспособность модели."""
        try:
            # Проверяем наличие всех необходимых папок и файлов
            required_dirs = ['am', 'graph', 'conf', 'ivector']
            required_files = ['README', 'decode.py']
            
            # Проверяем папки
            for dir_name in required_dirs:
                dir_path = model_dir / dir_name
                if not dir_path.exists():
                    self.stdout.write(
                        self.style.ERROR(f"❌ Не найдена папка: {dir_name}")
                    )
                    return False
                else:
                    # Проверяем, что папка не пустая
                    if not any(dir_path.iterdir()):
                        self.stdout.write(
                            self.style.WARNING(f"⚠️ Папка {dir_name} пустая")
                        )
            
            # Проверяем файлы
            for file_name in required_files:
                file_path = model_dir / file_name
                if not file_path.exists():
                    self.stdout.write(
                        self.style.ERROR(f"❌ Не найден файл: {file_name}")
                    )
                    return False
            
            # Проверяем размер модели (должна быть достаточно большой)
            total_size_mb = sum(
                f.stat().st_size for f in model_dir.rglob('*') if f.is_file()
            ) / (1024 * 1024)
            
            self.stdout.write(f"✅ Общий размер модели: {total_size_mb:.1f} MB")
            
            if total_size_mb < 100:  # Модель должна быть больше 100MB
                self.stdout.write(
                    self.style.WARNING("⚠️ Общий размер модели меньше ожидаемого")
                )
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при проверке модели: {e}")
            )
            return False
    
    def _cleanup(self, temp_dir: Path):
        """Очищает временные файлы."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️ Предупреждение: не удалось очистить временные файлы: {e}")
            )
