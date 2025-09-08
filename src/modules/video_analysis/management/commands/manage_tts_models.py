"""
Django команда для управления TTS моделями Silero
"""

import os
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.config.settings.static import TRAINED_MODELS_PATH, PACKAGES_PATH


class Command(BaseCommand):
    help = 'Управление TTS моделями Silero'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['list', 'install', 'remove', 'test'],
            help='Действие: list (показать), install (установить), remove (удалить), test (тестировать)'
        )
        parser.add_argument(
            '--language',
            type=str,
            default='ru',
            choices=['ru', 'en', 'fr', 'de', 'es'],
            help='Язык TTS модели'
        )
        parser.add_argument(
            '--speaker',
            type=str,
            help='ID спикера'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Применить ко всем моделям (для remove)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_models()
        elif action == 'install':
            self.install_model(options)
        elif action == 'remove':
            self.remove_model(options)
        elif action == 'test':
            self.test_model(options)

    def list_models(self):
        """Показывает список установленных TTS моделей"""
        tts_models_dir = Path(TRAINED_MODELS_PATH) / 'silero-tts'
        
        if not tts_models_dir.exists():
            self.stdout.write(
                self.style.WARNING('Папка с TTS моделями не найдена')
            )
            return
        
        models = []
        for model_dir in tts_models_dir.iterdir():
            if model_dir.is_dir():
                config_path = model_dir / 'config.json'
                if config_path.exists():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        
                        # Подсчитываем размер
                        total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                        size_mb = total_size / (1024 * 1024)
                        
                        models.append({
                            'name': model_dir.name,
                            'language': config.get('language', 'unknown'),
                            'speaker': config.get('speaker', 'unknown'),
                            'size_mb': size_mb,
                            'path': str(model_dir)
                        })
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Ошибка чтения конфига {config_path}: {e}')
                        )
        
        if not models:
            self.stdout.write(
                self.style.WARNING('Установленные TTS модели не найдены')
            )
            self.stdout.write('Для установки модели выполните:')
            self.stdout.write('python manage.py install_tts_model --language ru --speaker v3_1_ru')
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Найдено {len(models)} установленных TTS моделей:')
        )
        self.stdout.write('')
        
        for model in models:
            self.stdout.write(f"📁 {model['name']}")
            self.stdout.write(f"   Язык: {model['language']}")
            self.stdout.write(f"   Спикер: {model['speaker']}")
            self.stdout.write(f"   Размер: {model['size_mb']:.1f} MB")
            self.stdout.write(f"   Путь: {model['path']}")
            self.stdout.write('')

    def install_model(self, options):
        """Устанавливает TTS модель"""
        from django.core.management import call_command
        
        language = options['language']
        speaker = options.get('speaker')
        
        # Определяем спикера по умолчанию для языка
        default_speakers = {
            'ru': 'v3_1_ru',
            'en': 'v3_en',
            'fr': 'v3_fr',
            'de': 'v3_de',
            'es': 'v3_es'
        }
        
        if not speaker:
            speaker = default_speakers.get(language, 'v3_1_ru')
        
        # Убедимся, что локальный репозиторий Silero установлен
        call_command('install_silero_repo')

        self.stdout.write(f'Установка модели: язык={language}, спикер={speaker}')
        
        try:
            call_command('install_tts_model', language=language, speaker=speaker)
        except Exception as e:
            raise CommandError(f'Ошибка при установке модели: {e}')

    def remove_model(self, options):
        """Удаляет TTS модель"""
        import shutil
        
        tts_models_dir = Path(TRAINED_MODELS_PATH) / 'silero-tts'
        
        if options.get('all'):
            # Удаляем все модели
            if tts_models_dir.exists():
                shutil.rmtree(tts_models_dir)
                self.stdout.write(
                    self.style.SUCCESS('Все TTS модели удалены')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Папка с TTS моделями не найдена')
                )
            return
        
        language = options['language']
        speaker = options.get('speaker', 'v3_1_ru')
        
        model_dir = tts_models_dir / f'{language}_{speaker}'
        
        if model_dir.exists():
            shutil.rmtree(model_dir)
            self.stdout.write(
                self.style.SUCCESS(f'Модель {language}_{speaker} удалена')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Модель {language}_{speaker} не найдена')
            )

    def test_model(self, options):
        """Тестирует TTS модель"""
        language = options['language']
        speaker = options.get('speaker', 'v3_1_ru')
        
        # Импортируем функцию генерации TTS
        try:
            from src.modules.video_analysis.scripts import generate_tts_audio
        except ImportError as e:
            raise CommandError(f'Не удалось импортировать TTS функции: {e}')
        
        # Тестовые тексты
        test_texts = {
            'ru': 'Привет! Это тест русской TTS модели Silero.',
            'en': 'Hello! This is a test of English TTS model.',
            'fr': 'Bonjour! Ceci est un test du modèle TTS français.',
            'de': 'Hallo! Dies ist ein Test des deutschen TTS-Modells.',
            'es': 'Hola! Esta es una prueba del modelo TTS español.'
        }
        
        test_text = test_texts.get(language, test_texts['ru'])
        
        # Создаем временный файл для тестирования
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            self.stdout.write(f'Тестирование модели {language}_{speaker}...')
            self.stdout.write(f'Текст: "{test_text}"')
            
            success = generate_tts_audio(
                text=test_text,
                output_path=temp_path,
                language=language,
                speaker=speaker,
                volume=0.8
            )
            
            if success:
                # Проверяем размер файла
                file_size = os.path.getsize(temp_path)
                duration_estimate = file_size / (48000 * 2)  # Примерная оценка
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Тест успешен!')
                )
                self.stdout.write(f'Размер файла: {file_size} байт')
                self.stdout.write(f'Примерная длительность: {duration_estimate:.1f} сек')
                self.stdout.write(f'Файл сохранен: {temp_path}')
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Тест не прошел')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при тестировании: {e}')
            )
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
            except:
                pass
