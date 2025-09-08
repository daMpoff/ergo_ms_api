import wave
import json
import os
import html
import subprocess
import logging
import time

from pathlib import Path

import pandas as pd
import platform

from vosk import Model, KaldiRecognizer
from moviepy.editor import VideoFileClip
from transformers import MarianMTModel, MarianTokenizer

from src.config.settings.static import MEDIA_ROOT, PACKAGES_PATH, TRAINED_MODELS_PATH

# Получаем логгер для модуля
logger = logging.getLogger('video_analysis')

# Импорт для GPU поддержки
import torch
from django.apps import apps

# Импорты для GPU batch-обработки vosk
try:
    from vosk import BatchModel, BatchRecognizer, GpuInit
    GPU_VOSK_AVAILABLE = True
    logger.info("GPU batch-обработка vosk: импорт успешен")
except ImportError:
    GPU_VOSK_AVAILABLE = False
    logger.warning("GPU batch-обработка vosk: импорт недоступен, используется обычная vosk")

# Константы
FRAME_CHUNK_SIZE = 4000  # Размер блока чтения аудио в фреймах
BATCH_CHUNK_SIZE = 8000  # Размер блока для batch-обработки GPU

FFMPEG_PATH = Path(PACKAGES_PATH) / 'ffmpeg' / 'bin' / 'ffmpeg.exe'

VIDEO_ANALYSIS_MEDIA_DIR = Path(MEDIA_ROOT) / 'video_analysis'
if not os.path.exists(VIDEO_ANALYSIS_MEDIA_DIR):
    os.makedirs(VIDEO_ANALYSIS_MEDIA_DIR, exist_ok=True)

# Глобальные переменные для кэширования моделей
_translation_model = None
_translation_tokenizer = None
_vosk_model = None
_batch_vosk_model = None
_tts_model = None
_device = None
_gpu_initialized = False


def _is_vosk_batch_supported() -> bool:
    """Возвращает True только если среда поддерживает CUDA batch Vosk.
    На практике официальный batch CUDA доступен лишь на Linux.
    """
    if not GPU_VOSK_AVAILABLE:
        return False
    if platform.system() != 'Linux':
        logger.warning(f"Vosk batch CUDA не поддерживается на {platform.system()}. Будет использована обычная модель.")
        return False
    if not torch.cuda.is_available():
        logger.warning("CUDA недоступна. Будет использована обычная модель Vosk.")
        return False
    return True

def init_gpu_vosk():
    """
    Инициализирует GPU для vosk batch-обработки
    
    Возвращает:
    bool: True если GPU успешно инициализирован, False иначе
    """
    global _gpu_initialized
    
    if _gpu_initialized:
        return True
    
    if not _is_vosk_batch_supported():
        logger.info("GPU batch-обработка vosk недоступна")
        return False
    
    try:
        GpuInit()
        _gpu_initialized = True
        logger.info("GPU для vosk успешно инициализирован")
        return True
    except Exception as e:
        logger.warning(f"Не удалось инициализировать GPU для vosk: {e}")
        _gpu_initialized = False
        return False


def get_device(use_gpu=None):
    """
    Определяет устройство для моделей (GPU/CPU)
    
    Параметры:
    use_gpu (bool): Принудительно использовать GPU (None - использовать настройки из конфига)
    
    Возвращает:
    str: 'cuda' или 'cpu'
    """
    global _device
    
    if _device is not None:
        return _device
    
    if use_gpu is None:
        # Получаем настройки из конфигурации приложения
        try:
            app_config = apps.get_app_config('video_analysis')
            use_gpu = app_config.USE_GPU
        except Exception:
            use_gpu = False
    
    if use_gpu and torch.cuda.is_available():
        _device = 'cuda'
        logger.info(f"Используется GPU: {torch.cuda.get_device_name()}")
    else:
        _device = 'cpu'
        if use_gpu and not torch.cuda.is_available():
            logger.warning("GPU запрошен, но недоступен. Используется CPU.")
        else:
            logger.info("Используется CPU")
    
    return _device

def replace_html_entities(text):
    # Преобразуем HTML-сущности в обычные символы
    return html.unescape(text)

def _load_translation_model(translation_model_name=None, use_gpu=None):
    """
    Ленивая загрузка модели перевода с поддержкой GPU
    """
    global _translation_model, _translation_tokenizer
    
    if _translation_model is None or _translation_tokenizer is None:
        logger.info("Загрузка модели перевода...")
        if translation_model_name is None:
            translation_model_name = str(Path(TRAINED_MODELS_PATH) / "opus-mt-ru-fr")
        
        device = get_device(use_gpu)
        
        _translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
        _translation_model = MarianMTModel.from_pretrained(translation_model_name)
        
        # Перемещаем модель на нужное устройство
        _translation_model = _translation_model.to(device)
        
        logger.info(f"Модель перевода загружена на {device}!")
    
    return _translation_model, _translation_tokenizer

def _load_vosk_model(model_path=None):
    """
    Ленивая загрузка модели Vosk (обычная версия)
    """
    global _vosk_model
    
    if _vosk_model is None:
        logger.info("Загрузка модели распознавания речи...")
        if model_path is None:
            model_path = str(Path(TRAINED_MODELS_PATH) / "vosk-model-ru-0.42")
        
        _vosk_model = Model(model_path)
        logger.info("Модель распознавания речи загружена!")
    
    return _vosk_model


def _load_batch_vosk_model(model_path=None):
    """
    Ленивая загрузка batch-модели Vosk для GPU обработки
    """
    global _batch_vosk_model
    
    if _batch_vosk_model is None and _is_vosk_batch_supported():
        logger.info("Загрузка batch-модели распознавания речи для GPU...")
        if model_path is None:
            model_path = str(Path(TRAINED_MODELS_PATH) / "vosk-model-ru-0.42")
        
        # Инициализируем GPU если еще не инициализирован
        if init_gpu_vosk():
            try:
                _batch_vosk_model = BatchModel(model_path)
                logger.info("Batch-модель распознавания речи для GPU загружена!")
            except Exception as e:
                logger.error(f"Ошибка при загрузке batch-модели: {e}. Среда: os={platform.system()}, cuda={torch.cuda.is_available()}")
                _batch_vosk_model = None
        else:
            logger.warning("GPU не инициализирован, batch-модель не загружена")
    
    return _batch_vosk_model


def _load_tts_model(use_gpu=None, language='ru', speaker='v3_1_ru'):
    """
    Ленивая загрузка TTS модели Silero из папки trained_models
    """
    global _tts_model
    
    # Проверяем, нужно ли загрузить модель заново (другой язык/спикер)
    if (_tts_model is None or 
        _tts_model.get('language') != language or 
        _tts_model.get('speaker') != speaker):
        logger.info("Загрузка TTS модели Silero...")
        try:
            import torch
            import json
            
            device = get_device(use_gpu)
            
            # Путь к локальной модели
            tts_models_dir = Path(TRAINED_MODELS_PATH) / 'silero-tts'
            model_dir = tts_models_dir / f'{language}_{speaker}'
            
            if model_dir.exists():
                # Загружаем локальную модель
                logger.info(f"Загрузка локальной TTS модели из {model_dir}")
                
                # Читаем конфигурацию
                config_path = model_dir / 'config.json'
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    logger.info(f"Конфигурация модели: {config}")
                else:
                    config = {
                        'language': language,
                        'speaker': speaker,
                        'sample_rate': 48000
                    }
                
                # Загружаем модель с torch.hub (для получения архитектуры)
                # Используем локальный репозиторий в packages
                try:
                    import sys as _sys
                    local_repo_dir = Path(PACKAGES_PATH) / 'silero-models'
                    repo_dir = str(local_repo_dir)
                    src_dir = str(local_repo_dir / 'src')
                    for p in (repo_dir, src_dir):
                        if os.path.isdir(p) and p not in _sys.path:
                            _sys.path.insert(0, p)
                except Exception as _e:
                    logger.warning(f"Не удалось подготовить sys.path для локального silero: {_e}")

                model, example_text = torch.hub.load(
                    repo_or_dir=repo_dir,
                    model='silero_tts',
                    language=language,
                    speaker=speaker,
                    source='local'
                )
                
                # Загружаем веса из локального файла
                model_path = model_dir / 'model.pt'
                if model_path.exists():
                    try:
                        state_dict = torch.load(model_path, map_location=device)
                        model.load_state_dict(state_dict)
                        logger.info("Загружены локальные веса модели")
                    except Exception as e:
                        logger.warning(f"Не удалось загрузить локальные веса: {e}, используем предзагруженную модель")
                
                model = model.to(device)
                _tts_model = {
                    'model': model,
                    'device': device,
                    'sample_rate': config.get('sample_rate', 48000),
                    'language': config.get('language', language),
                    'speaker': config.get('speaker', speaker)
                }
                
                logger.info(f"Локальная TTS модель загружена на {device}!")
                
            else:
                # Загружаем модель с torch.hub (fallback)
                logger.warning(f"Локальная модель не найдена в {model_dir}, загружаем с torch.hub")
                logger.info("Для установки локальной модели выполните: python manage.py install_tts_model")
                
                # Локальный путь также для fallback
                try:
                    import sys as _sys
                    local_repo_dir = Path(PACKAGES_PATH) / 'silero-models'
                    repo_dir = str(local_repo_dir)
                    src_dir = str(local_repo_dir / 'src')
                    for p in (repo_dir, src_dir):
                        if os.path.isdir(p) and p not in _sys.path:
                            _sys.path.insert(0, p)
                except Exception as _e:
                    logger.warning(f"Не удалось подготовить sys.path для локального silero: {_e}")

                model, example_text = torch.hub.load(
                    repo_or_dir=repo_dir,
                    model='silero_tts',
                    language=language,
                    speaker=speaker,
                    source='local'
                )
                
                model = model.to(device)
                _tts_model = {
                    'model': model,
                    'device': device,
                    'sample_rate': 48000,
                    'language': language,
                    'speaker': speaker
                }
                
                logger.info(f"TTS модель Silero загружена с torch.hub на {device}!")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке TTS модели: {e}")
            _tts_model = None
    
    return _tts_model


def generate_tts_audio(text, output_path, language='ru', speaker='v3_1_ru', volume=1.0):
    """
    Генерирует аудио из текста с помощью Silero TTS
    
    Параметры:
    text (str): Текст для озвучки
    output_path (str): Путь для сохранения аудио файла
    language (str): Язык озвучки ('ru', 'en', 'fr')
    speaker (str): Голос диктора
    volume (float): Громкость (0.0-1.0)
    
    Возвращает:
    bool: Успешность операции
    """
    try:
        import torch
        import torchaudio
        import numpy as np
        
        # Загружаем модель с нужным языком и спикером
        tts_data = _load_tts_model(language=language, speaker=speaker)
        if not tts_data:
            logger.error("TTS модель не загружена")
            return False
        
        model = tts_data['model']
        device = tts_data['device']
        sample_rate = tts_data['sample_rate']
        model_language = tts_data.get('language', language)
        model_speaker = tts_data.get('speaker', speaker)
        
        logger.debug(f"Генерация TTS: язык={model_language}, спикер={model_speaker}, текст='{text[:50]}...'")
        
        # Генерируем аудио
        with torch.no_grad():
            audio = model.apply_tts(
                text=text,
                speaker=model_speaker,
                sample_rate=sample_rate
            )
        
        # Применяем громкость
        if volume != 1.0:
            audio = audio * volume
        
        # Ограничиваем значения
        audio = torch.clamp(audio, -1.0, 1.0)
        
        # Сохраняем в файл
        torchaudio.save(output_path, audio.unsqueeze(0).cpu(), sample_rate)
        
        logger.info(f"TTS аудио сохранено: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при генерации TTS аудио: {e}")
        return False


def generate_tts_from_subtitles(subtitles_data, output_dir, language='ru', speaker='v3_1_ru', volume=1.0):
    """
    Генерирует аудио файлы из данных субтитров
    
    Параметры:
    subtitles_data (list): Список словарей с данными субтитров
    output_dir (str): Директория для сохранения аудио файлов
    language (str): Язык озвучки
    speaker (str): Голос диктора
    volume (float): Громкость
    
    Возвращает:
    list: Список путей к созданным аудио файлам
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        audio_files = []
        
        for i, subtitle in enumerate(subtitles_data):
            # Выбираем текст в зависимости от языка
            if language == 'ru':
                text = subtitle.get('russian_text', '')
            else:
                text = subtitle.get('french_text', '')
            
            if not text.strip():
                continue
            
            # Генерируем имя файла
            audio_filename = f"tts_segment_{i+1:04d}.wav"
            audio_path = os.path.join(output_dir, audio_filename)
            
            # Генерируем аудио
            if generate_tts_audio(text, audio_path, language, speaker, volume):
                audio_files.append({
                    'path': audio_path,
                    'start_time': subtitle.get('start_time'),
                    'end_time': subtitle.get('end_time'),
                    'text': text
                })
            else:
                logger.warning(f"Не удалось сгенерировать аудио для сегмента {i+1}")
        
        logger.info(f"Сгенерировано {len(audio_files)} TTS аудио файлов")
        return audio_files
        
    except Exception as e:
        logger.error(f"Ошибка при генерации TTS из субтитров: {e}")
        return []


def combine_tts_audio_segments(audio_segments, output_path, video_duration=None):
    """
    Объединяет TTS аудио сегменты в один файл с правильными временными метками
    
    Параметры:
    audio_segments (list): Список аудио сегментов с временными метками
    output_path (str): Путь для сохранения объединенного файла
    video_duration (float): Длительность видео в секундах
    
    Возвращает:
    bool: Успешность операции
    """
    try:
        from pydub import AudioSegment
        from pydub.silence import Silence
        
        if not audio_segments:
            logger.warning("Нет аудио сегментов для объединения")
            return False
        
        # Определяем общую длительность
        if video_duration:
            total_duration_ms = int(video_duration * 1000)
        else:
            # Берем время последнего сегмента
            last_segment = audio_segments[-1]
            end_time = parse_srt_time_to_seconds(last_segment['end_time'])
            total_duration_ms = int(end_time * 1000)
        
        # Создаем пустой аудио трек
        combined_audio = AudioSegment.silent(duration=total_duration_ms)
        
        # Добавляем каждый сегмент в нужное место
        for segment in audio_segments:
            try:
                # Загружаем аудио сегмент
                audio = AudioSegment.from_wav(segment['path'])
                
                # Парсим время начала
                start_time_sec = parse_srt_time_to_seconds(segment['start_time'])
                start_time_ms = int(start_time_sec * 1000)
                
                # Накладываем аудио
                combined_audio = combined_audio.overlay(audio, position=start_time_ms)
                
            except Exception as e:
                logger.warning(f"Не удалось добавить сегмент {segment['path']}: {e}")
                continue
        
        # Сохраняем объединенный файл
        combined_audio.export(output_path, format="wav")
        
        logger.info(f"TTS аудио объединено и сохранено: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при объединении TTS аудио: {e}")
        return False


def parse_srt_time_to_seconds(srt_time):
    """
    Преобразует время SRT в секунды
    
    Параметры:
    srt_time (str): Время в формате HH:MM:SS,mmm
    
    Возвращает:
    float: Время в секундах
    """
    try:
        time_part, ms_part = srt_time.split(',')
        h, m, s = map(int, time_part.split(':'))
        ms = int(ms_part)
        return h * 3600 + m * 60 + s + ms / 1000.0
    except:
        return 0.0

def preload_models(translation_model_name=None, vosk_model_path=None, use_gpu=None):
    """
    Предварительная загрузка всех моделей для ускорения последующих операций
    
    Параметры:
    translation_model_name (str): Путь к модели перевода
    vosk_model_path (str): Путь к модели Vosk
    use_gpu (bool): Использовать GPU для моделей перевода и vosk
    """
    logger.info("Предварительная загрузка моделей...")
    _load_translation_model(translation_model_name, use_gpu)
    
    # Загружаем обычную модель vosk
    _load_vosk_model(vosk_model_path)
    
    # Если поддерживается batch и запрошен GPU, загружаем batch-модель
    if use_gpu and _is_vosk_batch_supported():
        batch_model = _load_batch_vosk_model(vosk_model_path)
        if batch_model:
            logger.info("Batch-модель vosk для GPU успешно загружена")
        else:
            logger.warning("Не удалось загрузить batch-модель vosk для GPU")
    
    # Загружаем TTS модель
    tts_model = _load_tts_model(use_gpu)
    if tts_model:
        logger.info("TTS модель Silero успешно загружена")
    else:
        logger.warning("Не удалось загрузить TTS модель")
    
    logger.info("Все модели загружены и готовы к использованию!")

def translate_text_ru_to_fr(text, model=None, tokenizer=None, use_gpu=None):
    """
    Переводит текст с русского на французский
    
    Параметры:
    text (str): Текст на русском языке
    model: Модель перевода (опционально, если не указана, используется кэшированная)
    tokenizer: Токенизатор (опционально, если не указан, используется кэшированный)
    use_gpu (bool): Использовать GPU для перевода
    
    Возвращает:
    str: Переведенный текст на французском
    """
    if not text.strip():
        return ""
    
    # Используем кэшированные модели, если не указаны другие
    if model is None or tokenizer is None:
        model, tokenizer = _load_translation_model(use_gpu=use_gpu)
    
    device = get_device(use_gpu)
    
    inputs = tokenizer(text, return_tensors="pt", padding=True)
    # Перемещаем входные данные на нужное устройство
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    translated = model.generate(**inputs, max_new_tokens=100)
    french_text = tokenizer.decode(translated[0], skip_special_tokens=True)

    french_text = replace_html_entities(french_text)

    return french_text

def format_srt_time(seconds):
    """
    Форматирует время для SRT файла: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

def get_video_resolution(video_path):
    """
    Получает разрешение видео с помощью moviepy
    
    Параметры:
    video_path (str): Путь к видеофайлу
    
    Возвращает:
    tuple: (ширина, высота) или (1920, 1080) по умолчанию
    """
    try:
        from moviepy.editor import VideoFileClip
        with VideoFileClip(video_path) as video:
            return video.w, video.h
    except Exception as e:
        logger.warning(f"Не удалось получить разрешение видео {video_path}: {e}")
        return 1920, 1080  # Возвращаем разрешение по умолчанию

def calculate_max_chars_per_line(font_size, video_width, margin_percent=10):
    """
    Рассчитывает максимальное количество символов в строке субтитров
    на основе размера шрифта и ширины видео
    
    Параметры:
    font_size (int): Размер шрифта в пикселях
    video_width (int): Ширина видео в пикселях
    margin_percent (int): Процент отступов от краев (по умолчанию 10%)
    
    Возвращает:
    int: Максимальное количество символов в строке
    """
    # Примерная ширина символа в пикселях (для моноширинного шрифта)
    # Для пропорциональных шрифтов используем коэффициент 0.6
    char_width_ratio = 0.6
    avg_char_width = font_size * char_width_ratio
    
    # Вычисляем доступную ширину с учетом отступов
    margin = video_width * (margin_percent / 100)
    available_width = video_width - (2 * margin)
    
    # Рассчитываем максимальное количество символов
    max_chars = int(available_width / avg_char_width)
    
    # Ограничиваем минимальным и максимальным значением
    max_chars = max(20, min(max_chars, 80))  # От 20 до 80 символов
    
    logger.debug(f"Расчет символов: font_size={font_size}, video_width={video_width}, "
                f"char_width={avg_char_width:.1f}, available_width={available_width:.0f}, "
                f"max_chars={max_chars}")
    
    return max_chars

def split_long_text(text, max_chars_per_line=50):
    """
    Разбивает длинный текст на более короткие сегменты для субтитров
    
    Параметры:
    text (str): Исходный текст
    max_chars_per_line (int): Максимальное количество символов в одной строке
    
    Возвращает:
    list: Список коротких текстовых сегментов
    """
    if len(text) <= max_chars_per_line:
        return [text]
    
    # Разбиваем текст на предложения
    sentences = []
    current_sentence = ""
    
    # Простая разбивка по знакам препинания
    for char in text:
        current_sentence += char
        if char in '.!?':
            sentences.append(current_sentence.strip())
            current_sentence = ""
    
    # Добавляем остаток, если есть
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
    
    # Если предложений нет, разбиваем по словам
    if not sentences:
        sentences = [text]
    
    # Группируем предложения в сегменты
    segments = []
    current_segment = ""
    
    for sentence in sentences:
        # Если предложение слишком длинное само по себе, разбиваем его по словам
        if len(sentence) > max_chars_per_line:
            # Сначала добавляем текущий сегмент, если он не пустой
            if current_segment.strip():
                segments.append(current_segment.strip())
                current_segment = ""
            
            # Разбиваем длинное предложение по словам
            words = sentence.split()
            temp_segment = ""
            
            for word in words:
                if len(temp_segment + " " + word) <= max_chars_per_line:
                    temp_segment = (temp_segment + " " + word).strip()
                else:
                    if temp_segment.strip():
                        segments.append(temp_segment.strip())
                    temp_segment = word
            
            if temp_segment.strip():
                current_segment = temp_segment
        else:
            # Проверяем, поместится ли предложение в текущий сегмент
            if len(current_segment + " " + sentence) <= max_chars_per_line:
                current_segment = (current_segment + " " + sentence).strip()
            else:
                # Добавляем текущий сегмент и начинаем новый
                if current_segment.strip():
                    segments.append(current_segment.strip())
                current_segment = sentence
    
    # Добавляем последний сегмент
    if current_segment.strip():
        segments.append(current_segment.strip())
    
    return segments if segments else [text]


class GpuVoskProcessor:
    """
    Класс для batch-обработки аудио с помощью GPU-ускоренного vosk
    """
    
    def __init__(self, model_path=None, sample_rate=16000):
        """
        Инициализация процессора
        
        Args:
            model_path: Путь к модели vosk
            sample_rate: Частота дискретизации аудио
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.batch_model = None
        self.recognizers = []
        self.results = []
        self.ended = set()
        
    def initialize(self):
        """
        Инициализирует batch-модель и GPU
        
        Returns:
            bool: True если инициализация успешна
        """
        if not GPU_VOSK_AVAILABLE:
            logger.error("GPU batch-обработка vosk недоступна")
            return False
            
        try:
            # Инициализируем GPU
            if not init_gpu_vosk():
                return False
                
            # Загружаем batch-модель
            self.batch_model = _load_batch_vosk_model(self.model_path)
            if not self.batch_model:
                logger.error("Не удалось загрузить batch-модель")
                return False
                
            logger.info("GPU vosk процессор успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации GPU vosk процессора: {e}")
            return False
    
    def prepare_audio_chunks(self, wav_file_path, chunk_size=BATCH_CHUNK_SIZE):
        """
        Подготавливает аудио файл для batch-обработки, разбивая на чанки
        
        Args:
            wav_file_path: Путь к WAV файлу
            chunk_size: Размер чанка в байтах
            
        Returns:
            list: Список аудио чанков или None при ошибке
        """
        try:
            wf = wave.open(wav_file_path, "rb")
            
            # Проверяем формат
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                logger.error("Аудиофайл должен быть в формате WAV mono PCM")
                wf.close()
                return None
            
            # Проверяем частоту дискретизации
            if wf.getframerate() != self.sample_rate:
                logger.warning(f"Частота дискретизации файла ({wf.getframerate()}) не соответствует ожидаемой ({self.sample_rate})")
            
            # Читаем весь файл и разбиваем на чанки
            chunks = []
            while True:
                data = wf.readframes(chunk_size)
                if len(data) == 0:
                    break
                chunks.append(data)
            
            wf.close()
            logger.info(f"Аудио разбито на {len(chunks)} чанков для batch-обработки")
            return chunks
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке аудио чанков: {e}")
            return None
    
    def process_audio_batch(self, audio_chunks):
        """
        Обрабатывает аудио чанки с помощью GPU batch-обработки
        
        Args:
            audio_chunks: Список аудио чанков
            
        Returns:
            list: Список результатов распознавания
        """
        if not self.batch_model:
            logger.error("Batch-модель не инициализирована")
            return []
        
        try:
            # Создаем распознаватели для каждого чанка
            self.recognizers = [BatchRecognizer(self.batch_model, self.sample_rate) for _ in audio_chunks]
            self.results = [""] * len(audio_chunks)
            self.ended = set()
            
            total_samples = 0
            start_time = time.time()
            
            # Основной цикл обработки
            chunk_index = 0
            while True:
                # Подаем данные в распознаватели
                for i, chunk in enumerate(audio_chunks):
                    if i in self.ended:
                        continue
                    
                    if chunk_index < len(chunk) if isinstance(chunk, (list, bytes)) else False:
                        # Берем следующую порцию данных из чанка
                        if isinstance(chunk, bytes):
                            data_portion = chunk[chunk_index:chunk_index + FRAME_CHUNK_SIZE] if chunk_index < len(chunk) else b""
                        else:
                            data_portion = b""
                        
                        if len(data_portion) == 0:
                            self.recognizers[i].FinishStream()
                            self.ended.add(i)
                            continue
                            
                        self.recognizers[i].AcceptWaveform(data_portion)
                        total_samples += len(data_portion)
                    else:
                        self.recognizers[i].FinishStream()
                        self.ended.add(i)
                
                # Ждем результатов от GPU
                self.batch_model.Wait()
                
                # Получаем и добавляем результаты
                for i in range(len(audio_chunks)):
                    result = self.recognizers[i].Result()
                    if len(result) != 0:
                        result_data = json.loads(result)
                        text = result_data.get("text", "")
                        if text:
                            self.results[i] = self.results[i] + " " + text if self.results[i] else text
                
                # Проверяем, закончили ли обработку всех чанков
                if len(self.ended) == len(audio_chunks):
                    break
                    
                chunk_index += FRAME_CHUNK_SIZE
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Логируем статистику производительности
            audio_duration = total_samples / self.sample_rate / 2  # 16-bit samples
            speedup = audio_duration / processing_time if processing_time > 0 else 0
            
            logger.info(f"GPU batch-обработка завершена:")
            logger.info(f"  Обработано {audio_duration:.3f} сек аудио за {processing_time:.3f} сек")
            logger.info(f"  Ускорение: {speedup:.3f}x RT")
            
            # Фильтруем пустые результаты и возвращаем
            filtered_results = [result.strip() for result in self.results if result.strip()]
            return filtered_results
            
        except Exception as e:
            logger.error(f"Ошибка при GPU batch-обработке: {e}")
            return []
    
    def cleanup(self):
        """
        Очищает ресурсы процессора
        """
        self.recognizers = []
        self.results = []
        self.ended = set()
        # batch_model остается в кеше для повторного использования

def split_subtitle_with_timing(subtitle_data, max_chars_per_line=50, font_size=24, video_width=1920):
    """
    Разбивает субтитр с длинным текстом на несколько коротких субтитров с пропорциональными временными метками
    
    Параметры:
    subtitle_data (dict): Данные субтитра с ключами start_time, end_time, russian_text, french_text
    max_chars_per_line (int): Максимальное количество символов в строке (если не рассчитывается автоматически)
    font_size (int): Размер шрифта субтитров в пикселях
    video_width (int): Ширина видео в пикселях
    
    Возвращает:
    list: Список субтитров с короткими текстами
    """
    # Рассчитываем максимальное количество символов на основе размера шрифта и ширины видео
    calculated_max_chars = calculate_max_chars_per_line(font_size, video_width)
    actual_max_chars = min(max_chars_per_line, calculated_max_chars)
    
    logger.debug(f"Разбивка субтитра: font_size={font_size}, video_width={video_width}, "
                f"calculated_max={calculated_max_chars}, actual_max={actual_max_chars}")
    
    # Разбиваем французский текст (он отображается в субтитрах)
    french_segments = split_long_text(subtitle_data['french_text'], actual_max_chars)
    
    # Если текст не нужно разбивать, возвращаем исходный субтитр
    if len(french_segments) <= 1:
        return [subtitle_data]
    
    # Разбиваем русский текст пропорционально
    russian_segments = split_long_text(subtitle_data['russian_text'], actual_max_chars)
    
    # Если количество сегментов не совпадает, дублируем сегменты
    if len(russian_segments) < len(french_segments):
        # Дублируем последний русский сегмент
        while len(russian_segments) < len(french_segments):
            russian_segments.append(russian_segments[-1] if russian_segments else "")
    elif len(french_segments) < len(russian_segments):
        # Дублируем последний французский сегмент
        while len(french_segments) < len(russian_segments):
            french_segments.append(french_segments[-1] if french_segments else "")
    
    # Парсим временные метки
    def parse_srt_time(time_str):
        """Преобразует время SRT в секунды"""
        try:
            time_part, ms_part = time_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            return h * 3600 + m * 60 + s + ms / 1000.0
        except:
            return 0.0
    
    start_seconds = parse_srt_time(subtitle_data['start_time'])
    end_seconds = parse_srt_time(subtitle_data['end_time'])
    total_duration = end_seconds - start_seconds
    
    # Создаем список разбитых субтитров
    split_subtitles = []
    segment_duration = total_duration / len(french_segments)
    
    for i, (french_text, russian_text) in enumerate(zip(french_segments, russian_segments)):
        segment_start = start_seconds + i * segment_duration
        segment_end = start_seconds + (i + 1) * segment_duration
        
        # Для последнего сегмента используем точное время окончания
        if i == len(french_segments) - 1:
            segment_end = end_seconds
        
        split_subtitles.append({
            'start_time': format_srt_time(segment_start),
            'end_time': format_srt_time(segment_end),
            'russian_text': russian_text,
            'french_text': french_text
        })
    
    return split_subtitles

def extract_audio(video_path, output_audio_path):
    """
    Извлекает аудио из видео и сохраняет как моно WAV PCM
    
    Параметры:
    video_path (str): Путь к видеофайлу
    output_audio_path (output_audio_path): Путь для сохранения аудио
    
    Возвращает:
    bool: Успешность операции
    """
    try:
        logger.info(f"Начинаю извлечение аудио из {video_path}")
        logger.debug(f"Выходной файл: {output_audio_path}")
        
        video = VideoFileClip(video_path)
        audio = video.audio
        
        if audio is None:
            logger.error("Ошибка: видео не содержит аудио")
            video.close()
            return False
        
        # Указываем параметры для создания моно WAV PCM
        audio.write_audiofile(
            output_audio_path,
            codec='pcm_s16le',  # PCM формат
            ffmpeg_params=["-ac", "1"]  # Один канал (моно)
        )
        
        audio.close()
        video.close()
        
        # Проверяем, что файл создался
        if os.path.exists(output_audio_path):
            file_size = os.path.getsize(output_audio_path)
            logger.info(f"Аудио успешно извлечено. Размер файла: {file_size} байт")
            return True
        else:
            logger.error("Ошибка: выходной аудиофайл не создался")
            return False
            
    except Exception as e:
        import traceback
        logger.error(f"Ошибка при извлечении аудио: {e}")
        logger.error(f"Полный стек ошибки:\n{traceback.format_exc()}")
        return False

def convert_wav_to_bilingual_subtitles(wav_file_path, output_srt_path=None, model_path=None, translation_model_name=None, use_gpu=None, subtitle_lines_count=1, video_path=None, font_size=24):
    """
    Преобразует WAV файл в двуязычные субтитры формата SRT (русский + французский)
    
    Параметры:
    wav_file_path (str): Путь к WAV файлу
    output_srt_path (str): Путь для сохранения SRT файла (опционально)
    model_path (str): Путь к модели Vosk для русского языка
    translation_model_name (str): Путь к модели перевода
    use_gpu (bool): Использовать GPU для перевода
    subtitle_lines_count (int): Количество строк субтитров одновременно
    video_path (str): Путь к видеофайлу для получения разрешения (опционально)
    font_size (int): Размер шрифта субтитров для расчета максимальной длины строки
    
    Возвращает:
    tuple: (путь к созданному SRT файлу, DataFrame с результатами распознавания и перевода)
    """
    import time
    
    # Получаем разрешение видео для точного расчета длины строк
    video_width = 1920  # По умолчанию
    if video_path and os.path.exists(video_path):
        try:
            video_width, video_height = get_video_resolution(video_path)
            logger.info(f"Разрешение видео: {video_width}x{video_height}")
        except Exception as e:
            logger.warning(f"Не удалось получить разрешение видео, используем {video_width}x1080: {e}")
    else:
        logger.debug(f"Видеофайл не указан или не найден, используем разрешение по умолчанию: {video_width}x1080")
    
    # Загружаем модели (используем кэшированные, если уже загружены)
    translation_model, tokenizer = _load_translation_model(translation_model_name, use_gpu)
    vosk_model = _load_vosk_model(model_path)
    
    # Создаем имя для SRT файла, если не указано
    if not output_srt_path:
        output_srt_path = os.path.splitext(wav_file_path)[0] + "_bilingual.srt"
    else:
        # Убеждаемся, что путь - это строка
        output_srt_path = str(output_srt_path)
    
    # Открываем WAV файл
    try:
        wf = wave.open(wav_file_path, "rb")
    except Exception as e:
        logger.error(f"Ошибка при открытии WAV файла {wav_file_path}: {e}")
        return None, None
    
    # Проверяем частоту дискретизации
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        logger.error("Аудиофайл должен быть в формате WAV mono PCM")
        wf.close()
        return None, None
    
    # Получаем частоту дискретизации для расчета времени
    frame_rate = float(wf.getframerate())  # Явно приводим к float
    
    # Проверяем корректность полученных значений
    if frame_rate <= 0:
        logger.error(f"Ошибка: некорректная частота дискретизации: {frame_rate}")
        wf.close()
        return None, None
    
    # Создаем распознаватель с указанной частотой дискретизации
    recognizer = KaldiRecognizer(vosk_model, frame_rate)
    recognizer.SetWords(True)  # Включаем вывод слов и временных меток
    
    # Открываем файл для записи субтитров в формате SRT
    with open(output_srt_path, "w", encoding="utf-8") as f:
        pass  # Просто создаем пустой файл
    
    # Переменные для отслеживания прогресса и нумерации субтитров
    total_frames = int(wf.getnframes())  # Явно приводим к int
    processed_frames = 0
    subtitle_count = 0
    
    # Проверяем корректность полученных значений
    if total_frames <= 0:
        logger.error(f"Ошибка: некорректное количество кадров: {total_frames}")
        wf.close()
        return None, None
    
    # Создаем список для хранения результатов для DataFrame
    recognition_results = []
    
    # Список для накопления всех субтитров перед группировкой
    all_subtitles = []
    
    # Статистика времени
    total_translation_time = 0
    translation_count = 0
    
    # Читаем аудиофайл по частям и распознаем
    while True:
        data = wf.readframes(FRAME_CHUNK_SIZE)  # Читаем блок данных
        if len(data) == 0:
            break
        
        processed_frames += FRAME_CHUNK_SIZE
        
        # Дополнительная отладочная информация каждые 10000 кадров
        if processed_frames % 10000 == 0:
            logger.debug(f"processed_frames = {processed_frames} (тип: {type(processed_frames)})")
        
        # Проверяем, что переменные являются числами
        if not isinstance(processed_frames, (int, float)) or not isinstance(total_frames, (int, float)):
            logger.error(f"Ошибка: неверные типы переменных - processed_frames: {type(processed_frames)}, total_frames: {type(total_frames)}")
            break
            
        # Безопасное вычисление прогресса
        try:
            progress = min(100, int(processed_frames / total_frames * 100))
            logger.debug(f"Прогресс распознавания: {progress}%")
        except (TypeError, ZeroDivisionError) as e:
            logger.error(f"Ошибка при вычислении прогресса: {e}")
            break
        
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            
            # Извлекаем текст
            ru_text = result.get('text', '')
            
            if ru_text:
                # Переводим текст на французский
                translation_start = time.time()
                fr_text = translate_text_ru_to_fr(ru_text, use_gpu=use_gpu)
                translation_time = time.time() - translation_start
                total_translation_time += translation_time
                translation_count += 1
                
                # Получаем временные метки для фрагмента
                start_time = None
                end_time = None
                
                if 'result' in result and result['result']:
                    start_time = result['result'][0]['start']
                    end_time = result['result'][-1]['end']
                else:
                    # Если нет детальной информации о словах, используем приблизительное время
                    try:
                        current_frame = processed_frames - FRAME_CHUNK_SIZE
                        start_time = max(0, (current_frame - FRAME_CHUNK_SIZE) / frame_rate)
                        end_time = current_frame / frame_rate
                    except (TypeError, ZeroDivisionError) as e:
                        logger.error(f"Ошибка при вычислении времени: {e}")
                        start_time = 0
                        end_time = 1
                
                # Создаем данные субтитра
                subtitle_data = {
                    'start_time': format_srt_time(start_time),
                    'end_time': format_srt_time(end_time),
                    'russian_text': ru_text,
                    'french_text': fr_text
                }
                
                # Сохраняем результат для DataFrame
                recognition_results.append({
                    'id': len(recognition_results) + 1,
                    'start_time': subtitle_data['start_time'],
                    'end_time': subtitle_data['end_time'],
                    'russian_text': subtitle_data['russian_text'],
                    'french_text': subtitle_data['french_text']
                })
                
                # Разбиваем длинные субтитры на короткие сегменты с учетом размера шрифта
                split_segments = split_subtitle_with_timing(
                    subtitle_data, 
                    max_chars_per_line=80,  # Максимум для безопасности
                    font_size=font_size,
                    video_width=video_width
                )
                
                # Добавляем все сегменты в общий список
                all_subtitles.extend(split_segments)
    
    # Обрабатываем финальный результат
    final_result = json.loads(recognizer.FinalResult())
    final_ru_text = final_result.get('text', '')
    
    if final_ru_text:
        # Переводим финальный текст
        final_fr_text = translate_text_ru_to_fr(final_ru_text)
        
        # Получаем временные метки для финального фрагмента
        start_time = None
        end_time = None
        
        if 'result' in final_result and final_result['result']:
            start_time = final_result['result'][0]['start']
            end_time = final_result['result'][-1]['end']
        else:
            # Если нет детальной информации о словах, используем приблизительное время
            try:
                start_time = (processed_frames - FRAME_CHUNK_SIZE) / frame_rate
                end_time = processed_frames / frame_rate
            except (TypeError, ZeroDivisionError) as e:
                logger.error(f"Ошибка при вычислении финального времени: {e}")
                start_time = 0
                end_time = 1
        
        # Создаем данные финального субтитра
        final_subtitle_data = {
            'start_time': format_srt_time(start_time),
            'end_time': format_srt_time(end_time),
            'russian_text': final_ru_text,
            'french_text': final_fr_text
        }
        
        # Сохраняем финальный результат для DataFrame
        recognition_results.append({
            'id': len(recognition_results) + 1,
            'start_time': final_subtitle_data['start_time'],
            'end_time': final_subtitle_data['end_time'],
            'russian_text': final_subtitle_data['russian_text'],
            'french_text': final_subtitle_data['french_text']
        })
        
        # Разбиваем финальный длинный субтитр на короткие сегменты с учетом размера шрифта
        final_split_segments = split_subtitle_with_timing(
            final_subtitle_data, 
            max_chars_per_line=80,  # Максимум для безопасности
            font_size=font_size,
            video_width=video_width
        )
        
        # Добавляем все сегменты в общий список
        all_subtitles.extend(final_split_segments)
    
    # Теперь группируем и записываем все субтитры
    def write_grouped_subtitles_to_file():
        """Записывает все субтитры с правильной группировкой"""
        nonlocal subtitle_count
        
        # Группируем субтитры по subtitle_lines_count
        for i in range(0, len(all_subtitles), subtitle_lines_count):
            group = all_subtitles[i:i + subtitle_lines_count]
            subtitle_count += 1
            
            # Определяем время начала и окончания группы
            group_start_time = group[0]['start_time']
            group_end_time = group[-1]['end_time']
            
            # Объединяем тексты (только французский для SRT файла)
            group_text = '\\n'.join([item['french_text'] for item in group])
            
            # Записываем группу субтитров
            with open(output_srt_path, "a", encoding="utf-8") as f:
                f.write(f"{subtitle_count}\n")
                f.write(f"{group_start_time} --> {group_end_time}\n")
                f.write(f"{group_text}\n\n")
    
    # Записываем все субтитры с группировкой
    write_grouped_subtitles_to_file()
    
    logger.info(f"Распознавание и перевод завершены. Субтитры сохранены в файл {output_srt_path}")
    
    # Выводим статистику времени
    if translation_count > 0:
        avg_translation_time = total_translation_time / translation_count
        logger.info(f"Статистика перевода:")
        logger.info(f"  Всего переводов: {translation_count}")
        logger.info(f"  Общее время перевода: {total_translation_time:.2f} сек")
        logger.info(f"  Среднее время на перевод: {avg_translation_time:.3f} сек")
    
    # Закрываем WAV файл
    wf.close()
    
    # Создаем DataFrame с результатами
    df_results = pd.DataFrame(recognition_results)
    
    return output_srt_path, df_results


def convert_wav_to_bilingual_subtitles_gpu(wav_file_path, output_srt_path=None, model_path=None, 
                                         translation_model_name=None, use_gpu=True, 
                                         subtitle_lines_count=1, video_path=None, font_size=24):
    """
    GPU-ускоренная версия преобразования WAV файла в двуязычные субтитры формата SRT
    
    Параметры:
    wav_file_path (str): Путь к WAV файлу
    output_srt_path (str): Путь для сохранения SRT файла (опционально)
    model_path (str): Путь к модели Vosk для русского языка
    translation_model_name (str): Путь к модели перевода
    use_gpu (bool): Использовать GPU для обработки
    subtitle_lines_count (int): Количество строк субтитров одновременно
    video_path (str): Путь к видеофайлу для получения разрешения (опционально)
    font_size (int): Размер шрифта субтитров для расчета максимальной длины строки
    
    Возвращает:
    tuple: (путь к созданному SRT файлу, DataFrame с результатами распознавания и перевода)
    """
    import time
    
    # Проверяем доступность GPU batch-обработки
    if not use_gpu or not GPU_VOSK_AVAILABLE:
        logger.info("GPU batch-обработка недоступна или отключена, используем обычную версию")
        return convert_wav_to_bilingual_subtitles(
            wav_file_path, output_srt_path, model_path, translation_model_name, 
            use_gpu, subtitle_lines_count, video_path, font_size
        )
    
    # Получаем разрешение видео для точного расчета длины строк
    video_width = 1920  # По умолчанию
    if video_path and os.path.exists(video_path):
        try:
            video_width, video_height = get_video_resolution(video_path)
            logger.info(f"Разрешение видео: {video_width}x{video_height}")
        except Exception as e:
            logger.warning(f"Не удалось получить разрешение видео, используем {video_width}x1080: {e}")
    
    # Создаем имя для SRT файла, если не указано
    if not output_srt_path:
        output_srt_path = os.path.splitext(wav_file_path)[0] + "_bilingual.srt"
    else:
        output_srt_path = str(output_srt_path)
    
    # Загружаем модель перевода
    translation_model, tokenizer = _load_translation_model(translation_model_name, use_gpu)
    
    # Инициализируем GPU vosk процессор
    gpu_processor = GpuVoskProcessor(model_path, sample_rate=16000)
    if not gpu_processor.initialize():
        logger.warning("Не удалось инициализировать GPU vosk процессор, используем обычную версию")
        return convert_wav_to_bilingual_subtitles(
            wav_file_path, output_srt_path, model_path, translation_model_name, 
            use_gpu, subtitle_lines_count, video_path, font_size
        )
    
    try:
        start_time = time.time()
        
        # Подготавливаем аудио чанки
        logger.info("Подготовка аудио для GPU batch-обработки...")
        audio_chunks = gpu_processor.prepare_audio_chunks(wav_file_path)
        if not audio_chunks:
            logger.error("Не удалось подготовить аудио чанки")
            return None, None
        
        # Обрабатываем аудио с помощью GPU
        logger.info("Запуск GPU batch-обработки vosk...")
        recognition_results = gpu_processor.process_audio_batch(audio_chunks)
        
        if not recognition_results:
            logger.warning("GPU обработка не дала результатов, используем обычную версию")
            gpu_processor.cleanup()
            return convert_wav_to_bilingual_subtitles(
                wav_file_path, output_srt_path, model_path, translation_model_name, 
                use_gpu, subtitle_lines_count, video_path, font_size
            )
        
        # Переводим результаты на французский
        logger.info("Перевод результатов на французский...")
        translation_start = time.time()
        
        subtitles_data = []
        all_subtitles = []
        
        # Рассчитываем временные метки для каждого результата
        total_duration = len(audio_chunks) * BATCH_CHUNK_SIZE / 16000.0 / 2  # Примерная длительность
        segment_duration = total_duration / len(recognition_results) if recognition_results else 1
        
        for i, ru_text in enumerate(recognition_results):
            if not ru_text.strip():
                continue
                
            # Переводим на французский
            fr_text = translate_text_ru_to_fr(ru_text, translation_model, tokenizer, use_gpu)
            
            # Рассчитываем временные метки
            start_time_sec = i * segment_duration
            end_time_sec = (i + 1) * segment_duration
            
            # Создаем данные субтитра
            subtitle_data = {
                'start_time': format_srt_time(start_time_sec),
                'end_time': format_srt_time(end_time_sec),
                'russian_text': ru_text,
                'french_text': fr_text
            }
            
            # Сохраняем для DataFrame
            subtitles_data.append({
                'id': len(subtitles_data) + 1,
                'start_time': subtitle_data['start_time'],
                'end_time': subtitle_data['end_time'],
                'russian_text': subtitle_data['russian_text'],
                'french_text': subtitle_data['french_text']
            })
            
            # Разбиваем длинные субтитры на короткие сегменты
            split_segments = split_subtitle_with_timing(
                subtitle_data, 
                max_chars_per_line=80,
                font_size=font_size,
                video_width=video_width
            )
            
            all_subtitles.extend(split_segments)
        
        translation_time = time.time() - translation_start
        logger.info(f"Перевод завершен за {translation_time:.2f} сек")
        
        # Записываем субтитры в файл
        logger.info("Запись субтитров в SRT файл...")
        with open(output_srt_path, "w", encoding="utf-8") as f:
            subtitle_count = 0
            
            # Группируем субтитры по subtitle_lines_count
            for i in range(0, len(all_subtitles), subtitle_lines_count):
                group = all_subtitles[i:i + subtitle_lines_count]
                subtitle_count += 1
                
                # Определяем время начала и окончания группы
                group_start_time = group[0]['start_time']
                group_end_time = group[-1]['end_time']
                
                # Объединяем тексты (только французский для SRT файла)
                group_text = '\\n'.join([item['french_text'] for item in group])
                
                # Записываем группу субтитров
                f.write(f"{subtitle_count}\n")
                f.write(f"{group_start_time} --> {group_end_time}\n")
                f.write(f"{group_text}\n\n")
        
        # Создаем DataFrame с результатами
        df_results = pd.DataFrame(subtitles_data)
        
        total_time = time.time() - start_time
        logger.info(f"GPU обработка завершена за {total_time:.2f} сек")
        logger.info(f"Создано {len(subtitles_data)} сегментов субтитров")
        logger.info(f"Субтитры сохранены в файл {output_srt_path}")
        
        # Очищаем ресурсы
        gpu_processor.cleanup()
        
        return output_srt_path, df_results
        
    except Exception as e:
        logger.error(f"Ошибка при GPU обработке: {e}")
        gpu_processor.cleanup()
        
        # Fallback на обычную версию
        logger.info("Переключаемся на обычную обработку...")
        return convert_wav_to_bilingual_subtitles(
            wav_file_path, output_srt_path, model_path, translation_model_name, 
            use_gpu, subtitle_lines_count, video_path, font_size
        )


def add_subtitles_to_video(video_path, srt_path, output_video_path, ffmpeg_path=None, 
                          subtitle_lines_count=1, subtitle_font_size=24, 
                          subtitle_font_color='#FFFFFF', subtitle_background_color='#000000',
                          subtitle_background_transparent=False):
    """
    Добавляет субтитры к видео с помощью FFmpeg
    
    Параметры:
    video_path (str): Путь к исходному видео
    srt_path (str): Путь к файлу субтитров
    output_video_path (str): Путь для сохранения результата
    ffmpeg_path (str): Путь к исполняемому файлу FFmpeg
    subtitle_lines_count (int): Количество строк субтитров одновременно
    subtitle_font_size (int): Размер шрифта субтитров
    subtitle_font_color (str): Цвет шрифта в формате HEX
    subtitle_background_color (str): Цвет фона в формате HEX
    subtitle_background_transparent (bool): Прозрачный фон
    
    Возвращает:
    bool: Успешность операции
    """
    if ffmpeg_path is None:
        ffmpeg_path = str(FFMPEG_PATH)
    
    # Нормализуем пути для Windows
    video_path = os.path.normpath(video_path)
    srt_path = os.path.normpath(srt_path)
    output_video_path = os.path.normpath(output_video_path)
    ffmpeg_path = os.path.normpath(ffmpeg_path)
    
    # Проверяем существование файлов
    if not os.path.exists(video_path):
        logger.error(f"Ошибка: видеофайл не найден: {video_path}")
        return False
    
    if not os.path.exists(srt_path):
        logger.error(f"Ошибка: файл субтитров не найден: {srt_path}")
        return False
    
    # Создаём директорию для выходного файла, если её нет
    output_dir = os.path.dirname(output_video_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Правильное экранирование пути к файлу субтитров для Windows
    # Заменяем обратные слеши на прямые и экранируем двоеточие
    escaped_srt_path = srt_path.replace('\\', '/').replace(':', '\\\\:')
    
    # Преобразуем HEX цвета в формат FFmpeg (BGR)
    def hex_to_ffmpeg_color(hex_color):
        """Преобразует HEX цвет в формат FFmpeg (BGR)"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # FFmpeg использует формат BGR
            return f"&H{b:02X}{g:02X}{r:02X}&"
        return "&HFFFFFF&"  # Белый по умолчанию
    
    # Создаем стили для субтитров
    font_color_ffmpeg = hex_to_ffmpeg_color(subtitle_font_color)
    background_color_ffmpeg = hex_to_ffmpeg_color(subtitle_background_color)
    
    # Настройки стиля
    if subtitle_background_transparent:
        # Для прозрачного фона используем BorderStyle=0 (без фона)
        # Добавляем тень и легкую обводку для улучшения читаемости
        style_parts = [
            f'FontSize={subtitle_font_size}',
            f'PrimaryColour={font_color_ffmpeg}',
            'BorderStyle=0',  # Без фона
            'Outline=1',      # Тонкая обводка для читаемости
            f'OutlineColour=&H000000&',  # Черная обводка
            'Shadow=2',       # Тень для улучшения читаемости
            'BackColour=&H00000000',     # Прозрачный фон (альфа = 00)
        ]
    else:
        # Для непрозрачного фона используем BorderStyle=3 (фон вокруг текста)
        style_parts = [
            f'FontSize={subtitle_font_size}',
            f'PrimaryColour={font_color_ffmpeg}',
            f'OutlineColour={background_color_ffmpeg}',
            'BorderStyle=3',  # Фон вокруг текста
            'Outline=0'       # Без дополнительной обводки
        ]
    
    # Создаем команду с правильным экранированием
    style_string = ','.join(style_parts)
    vf_filter = f'subtitles={escaped_srt_path}:force_style=\'{style_string}\''
    
    # Логируем настройки субтитров для отладки
    logger.info(f"Настройки субтитров: прозрачный_фон={subtitle_background_transparent}, "
               f"размер_шрифта={subtitle_font_size}, цвет_шрифта={subtitle_font_color}, "
               f"цвет_фона={subtitle_background_color}")
    logger.debug(f"ASS стили: {style_string}")
    logger.debug(f"FFmpeg фильтр: {vf_filter}")
    
    command = [
        ffmpeg_path,
        '-i', video_path,
        '-vf', vf_filter,
        '-c:a', 'copy',
        output_video_path,
        '-y'  # Перезаписать выходной файл, если он существует
    ]
    
    try:
        logger.info(f"Выполняем команду FFmpeg: {' '.join(command)}")
        subprocess.run(command, check=True)
        logger.info(f"Субтитры успешно добавлены. Результат сохранен в {output_video_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при добавлении субтитров: {e}")
        logger.error(f"Команда, которая вызвала ошибку: {' '.join(command)}")
        return False


def add_tts_audio_to_video(video_path, tts_audio_path, output_video_path, ffmpeg_path=None, volume=1.0):
    """
    Добавляет TTS аудио к видео с помощью FFmpeg
    
    Параметры:
    video_path (str): Путь к исходному видео
    tts_audio_path (str): Путь к TTS аудио файлу
    output_video_path (str): Путь для сохранения результата
    ffmpeg_path (str): Путь к исполняемому файлу FFmpeg
    volume (float): Громкость TTS аудио (0.0-1.0)
    
    Возвращает:
    bool: Успешность операции
    """
    if ffmpeg_path is None:
        ffmpeg_path = str(FFMPEG_PATH)
    
    # Нормализуем пути для Windows
    video_path = os.path.normpath(video_path)
    tts_audio_path = os.path.normpath(tts_audio_path)
    output_video_path = os.path.normpath(output_video_path)
    ffmpeg_path = os.path.normpath(ffmpeg_path)
    
    # Проверяем существование файлов
    if not os.path.exists(video_path):
        logger.error(f"Ошибка: видеофайл не найден: {video_path}")
        return False
    
    if not os.path.exists(tts_audio_path):
        logger.error(f"Ошибка: TTS аудио файл не найден: {tts_audio_path}")
        return False
    
    # Создаём директорию для выходного файла, если её нет
    output_dir = os.path.dirname(output_video_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Команда FFmpeg для смешивания аудио
    command = [
        ffmpeg_path,
        '-i', video_path,      # Исходное видео
        '-i', tts_audio_path,  # TTS аудио
        '-filter_complex', f'[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2,volume={volume}',
        '-c:v', 'copy',        # Копируем видео без изменений
        '-c:a', 'aac',         # Кодируем аудио в AAC
        output_video_path,
        '-y'  # Перезаписать выходной файл, если он существует
    ]
    
    try:
        logger.info(f"Добавляем TTS аудио к видео...")
        logger.debug(f"Команда FFmpeg: {' '.join(command)}")
        subprocess.run(command, check=True)
        logger.info(f"TTS аудио успешно добавлено. Результат сохранен в {output_video_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при добавлении TTS аудио: {e}")
        logger.error(f"Команда, которая вызвала ошибку: {' '.join(command)}")
        return False