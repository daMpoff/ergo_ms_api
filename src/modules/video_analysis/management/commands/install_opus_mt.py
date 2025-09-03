"""
Django команда для установки opus-mt-ru-fr в папку trained_models/.
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
    """Команда для установки opus-mt-ru-fr."""
    
    help = 'Устанавливает opus-mt-ru-fr в папку trained_models/'
    
    def add_arguments(self, parser):
        """Добавляет аргументы команды."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно переустановить opus-mt-ru-fr, даже если он уже установлен',
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default='opus-mt-ru-fr',
            help='Название модели для установки (по умолчанию: opus-mt-ru-fr)',
        )
    
    def handle(self, *args, **options):
        """Выполнение команды."""
        try:
            # Определяем пути
            model_name = options['model_version']
            model_dir = Path(TRAINED_MODELS_PATH) / model_name
            temp_dir = Path(TRAINED_MODELS_PATH) / "temp_opus_mt"
            
            self.stdout.write("🚀 Начинаю установку opus-mt-ru-fr...")
            
            # Проверяем, не установлен ли уже opus-mt-ru-fr
            if self._is_model_installed(model_dir) and not options['force']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {model_name} уже установлен в trained_models/{model_name}/")
                )
                self.stdout.write(f"📁 Путь: {model_dir.absolute()}")
                return
            
            if options['force']:
                self.stdout.write("🔄 Принудительная переустановка opus-mt-ru-fr...")
            
            # Создаем временную папку
            temp_dir.mkdir(exist_ok=True)
            
            # Определяем URL для загрузки модели
            model_url = "https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/pytorch_model.bin"
            
            self.stdout.write(f"📥 Загружаю {model_name}...")
            
            # Загружаем основные файлы модели
            if not self._download_model_files(model_name, temp_dir):
                raise CommandError("Не удалось загрузить файлы модели")
            
            self.stdout.write("📦 Распаковываю и настраиваю модель...")
            
            # Настраиваем структуру папок
            if not self._setup_model_structure(temp_dir, model_dir):
                raise CommandError("Не удалось настроить структуру папок модели")
            
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
            raise CommandError(f"Ошибка при установке opus-mt-ru-fr: {e}")
    
    def _is_model_installed(self, model_dir: Path) -> bool:
        """Проверяет, установлен ли уже opus-mt-ru-fr."""
        # Проверяем наличие основных файлов модели
        required_files = [
            'pytorch_model.bin',
            'config.json',
            'vocab.json',
            'source.spm',
            'target.spm'
        ]
        
        for file_name in required_files:
            if not (model_dir / file_name).exists():
                return False
        return True
    
    def _download_model_files(self, model_name: str, temp_dir: Path) -> bool:
        """Загружает файлы модели."""
        try:
            # Список файлов для загрузки
            model_files = {
                'pytorch_model.bin': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/pytorch_model.bin',
                'config.json': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/config.json',
                'vocab.json': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/vocab.json',
                'source.spm': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/source.spm',
                'target.spm': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/target.spm',
                'tokenizer_config.json': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/tokenizer_config.json',
                'generation_config.json': 'https://huggingface.co/Helsinki-NLP/opus-mt-ru-fr/resolve/main/generation_config.json'
            }
            
            for file_name, url in model_files.items():
                file_path = temp_dir / file_name
                self.stdout.write(f"📥 Загружаю {file_name}...")
                
                try:
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    self.stdout.write(f"\r📥 Прогресс {file_name}: {progress:.1f}%", ending='')
                                    self.stdout.flush()
                    
                    self.stdout.write()  # Новая строка после прогресса
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Ошибка при загрузке {file_name}: {e}")
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при загрузке файлов модели: {e}")
            )
            return False
    
    def _setup_model_structure(self, temp_dir: Path, model_dir: Path) -> bool:
        """Настраивает структуру папок модели."""
        try:
            # Создаем целевую папку
            model_dir.mkdir(exist_ok=True)
            
            # Перемещаем все файлы из временной папки в целевую
            for file_path in temp_dir.iterdir():
                if file_path.is_file():
                    shutil.move(str(file_path), str(model_dir / file_path.name))
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при настройке структуры: {e}")
            )
            return False
    
    def _verify_model(self, model_dir: Path) -> bool:
        """Проверяет работоспособность модели."""
        try:
            # Проверяем наличие всех необходимых файлов
            required_files = [
                'pytorch_model.bin',
                'config.json',
                'vocab.json',
                'source.spm',
                'target.spm'
            ]
            
            for file_name in required_files:
                file_path = model_dir / file_name
                if not file_path.exists():
                    self.stdout.write(
                        self.style.ERROR(f"❌ Не найден файл: {file_name}")
                    )
                    return False
            
            # Проверяем размеры файлов (должны быть достаточно большими)
            pytorch_model = model_dir / 'pytorch_model.bin'
            if pytorch_model.exists():
                file_size_mb = pytorch_model.stat().st_size / (1024 * 1024)
                self.stdout.write(f"✅ Размер модели: {file_size_mb:.1f} MB")
                
                if file_size_mb < 100:  # Модель должна быть больше 100MB
                    self.stdout.write(
                        self.style.WARNING("⚠️ Размер модели меньше ожидаемого")
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
