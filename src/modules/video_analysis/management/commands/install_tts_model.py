"""
Django команда для установки TTS модели Silero в папку trained_models
"""

import os
import sys
import traceback
import logging

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.modules.video_analysis.apps import VideoAnalysisConfig

logger = logging.getLogger('video_analysis')


class Command(BaseCommand):
    help = 'Устанавливает TTS модель Silero в папку trained_models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--language',
            type=str,
            default='ru',
            choices=['ru', 'en', 'fr', 'de', 'es'],
            help='Язык TTS модели (по умолчанию: ru)'
        )
        parser.add_argument(
            '--speaker',
            type=str,
            default='v3_1_ru',
            help='ID спикера (по умолчанию: v3_1_ru)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно переустановить модель, если она уже существует'
        )

    def handle(self, *args, **options):
        language = options['language']
        speaker = options['speaker']
        force = options['force']
        
        # Подбираем корректный спикер по языку, если указан дефолт или не подходит
        # Базовые дефолты (будут уточнены после загрузки модели)
        default_speakers = {
            'ru': 'v3_1_ru',
            'en': 'v3_en',
            'fr': 'random',
            'de': 'random',
            'es': 'random',
        }
        if not speaker or speaker == 'v3_1_ru' and language != 'ru':
            speaker = default_speakers.get(language, 'v3_1_ru')
        
        self.stdout.write(
            self.style.SUCCESS(f'Начинаю установку TTS модели Silero...')
        )
        self.stdout.write(f'Язык: {language}')
        self.stdout.write(f'Спикер: {speaker}')
        
        # Создаем папку для TTS моделей
        tts_models_dir = Path(VideoAnalysisConfig.TTS_MODELS_DIR)
        tts_models_dir.mkdir(parents=True, exist_ok=True)
        
        # Путь к конкретной модели
        model_dir = tts_models_dir / f'{language}_{speaker}'
        
        if model_dir.exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'TTS модель уже установлена в {model_dir}. '
                    'Используйте --force для переустановки.'
                )
            )
            return
        
        try:
            # Импортируем необходимые библиотеки
            self.stdout.write('Импорт зависимостей...')
            import torch
            import torchaudio
            
            # Проверяем доступность устройства
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.stdout.write(f'Используемое устройство: {device}')
            
            # Создаем директорию модели
            if model_dir.exists():
                import shutil
                shutil.rmtree(model_dir)
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Определяем путь для сохранения модели
            model_filename = f'silero_tts_{language}_{speaker}.pt'
            model_path = model_dir / model_filename
            
            # Получаем путь к локальному репозиторию Silero
            silero_repo_path = VideoAnalysisConfig.SILERO_MODELS_PATH
            if not os.path.exists(silero_repo_path):
                raise CommandError(
                    f"Локальный репозиторий Silero не найден: {silero_repo_path}. \n"
                    f"Установите его командой: python manage.py install_silero_repo"
                )
            
            self.stdout.write(f'Загрузка модели Silero TTS из локального репозитория: {silero_repo_path}')
            self.stdout.write(f'Сохранение модели в: {model_path}')
            
            # Загружаем модель из локального репозитория с сохранением в указанный путь
            model, example_text = torch.hub.load(
                repo_or_dir=silero_repo_path,
                model='silero_tts',
                language=language,
                speaker=speaker,
                source='local',
                force_reload=force  # Принудительно перезагружает модель если force=True
            )
            
            self.stdout.write(f'Модель успешно загружена из локального репозитория')
            
            # Сохраняем модель в файл
            self.stdout.write(f'Сохранение модели в файл: {model_path}')
            try:
                # Пытаемся сохранить модель
                if hasattr(model, 'state_dict'):
                    torch.save(model.state_dict(), model_path)
                else:
                    # Пробуем полное сохранение объекта
                    torch.save(model, model_path)
                self.stdout.write(f'Модель успешно сохранена в: {model_path}')
            except Exception as save_err:
                self.stdout.write(self.style.WARNING(
                    f"Не удалось сохранить модель в файл ({save_err}). "
                    f"Модель будет загружаться из локального репозитория при использовании."
                ))
            
            # Сохраняем конфигурацию модели
            config = {
                'language': language,
                'speaker': speaker,
                'model_type': 'silero_tts',
                'model_path': str(model_path),
                'silero_repo_path': silero_repo_path,
                'sample_rate': 48000,
                'device': device
            }
            
            import json
            config_path = model_dir / 'config.json'
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Сохраняем пример текста
            example_path = model_dir / 'example.txt'
            with open(example_path, 'w', encoding='utf-8') as f:
                f.write(example_text)
            
            # Тестируем модель
            self.stdout.write('Тестирование модели...')
            test_text = "Привет, это тест TTS модели Silero." if language == 'ru' else (example_text or "Bonjour, ceci est un test du modèle TTS.")
            # Валидируем спикера согласно списку модели
            model_speakers = getattr(model, 'speakers', None)
            test_speaker = speaker
            if isinstance(model_speakers, (list, tuple)) and model_speakers:
                if speaker not in model_speakers:
                    # Выбираем первый доступный либо random
                    test_speaker = 'random' if 'random' in model_speakers else model_speakers[0]
            
            with torch.no_grad():
                audio = model.apply_tts(
                    text=test_text,
                    speaker=test_speaker,
                    sample_rate=48000
                )
            
            # Сохраняем тестовое аудио
            test_audio_path = model_dir / 'test_audio.wav'
            torchaudio.save(str(test_audio_path), audio.unsqueeze(0), 48000)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ TTS модель успешно установлена в {model_dir}'
                )
            )
            self.stdout.write(f'Модель сохранена в: {model_path}')
            self.stdout.write(f'Конфигурация: {config_path}')
            self.stdout.write(f'Тестовое аудио: {test_audio_path}')
            
            # Выводим информацию о размере
            total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            self.stdout.write(f'Размер установленной модели: {size_mb:.1f} MB')
            
        except ImportError as e:
            tb = traceback.format_exc()
            details = [
                f"Импортная ошибка: {e}",
                f"model_path={locals().get('model_path', None)}",
                f"model_dir={locals().get('model_dir', None)}",
                "Traceback:",
                tb
            ]
            msg = "\n".join(details)
            logger.error(msg)
            raise CommandError(
                f'Не удалось импортировать необходимые библиотеки: {e}. '\
                f'Убедитесь, что установлены torch, torchaudio.\n{msg}'
            )
        except Exception as e:
            tb = traceback.format_exc()
            details = [
                f"Ошибка при установке TTS модели: {e}",
                f"model_path={locals().get('model_path', None)}",
                f"model_dir={locals().get('model_dir', None)}",
                "Traceback:",
                tb
            ]
            msg = "\n".join(details)
            logger.error(msg)
            raise CommandError(msg)

    def get_available_models(self):
        """Получает список доступных TTS моделей"""
        try:
            import torch
            # Это заглушка - в реальности нужно было бы обращаться к API Silero
            # для получения списка доступных моделей
            return {
                'ru': ['v3_1_ru', 'baya', 'kseniya', 'xenia', 'eugene'],
                'en': ['v3_en', 'en_0', 'en_1'],
                'fr': ['v3_fr'],
                'de': ['v3_de'],
                'es': ['v3_es']
            }
        except:
            return {}