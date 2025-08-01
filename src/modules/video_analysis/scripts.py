import wave
import json
import os
import html
import subprocess

from pathlib import Path

import pandas as pd

from vosk import Model, KaldiRecognizer
from moviepy.editor import VideoFileClip
from transformers import MarianMTModel, MarianTokenizer

from src.config.settings.static import MEDIA_ROOT, PACKAGES_PATH, TRAINED_MODELS_PATH

# Импорт для GPU поддержки
import torch
from django.apps import apps

# Константы
FRAME_CHUNK_SIZE = 4000  # Размер блока чтения аудио в фреймах

FFMPEG_PATH = Path(PACKAGES_PATH) / 'ffmpeg' / 'bin' / 'ffmpeg.exe'

VIDEO_ANALYSIS_MEDIA_DIR = Path(MEDIA_ROOT) / 'video_analysis'
if not os.path.exists(VIDEO_ANALYSIS_MEDIA_DIR):
    os.makedirs(VIDEO_ANALYSIS_MEDIA_DIR, exist_ok=True)

# Глобальные переменные для кэширования моделей
_translation_model = None
_translation_tokenizer = None
_vosk_model = None
_device = None

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
        print(f"Используется GPU: {torch.cuda.get_device_name()}")
    else:
        _device = 'cpu'
        if use_gpu and not torch.cuda.is_available():
            print("GPU запрошен, но недоступен. Используется CPU.")
        else:
            print("Используется CPU")
    
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
        print("Загрузка модели перевода...")
        if translation_model_name is None:
            translation_model_name = str(TRAINED_MODELS_PATH / "opus-mt-ru-fr")
        
        device = get_device(use_gpu)
        
        _translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
        _translation_model = MarianMTModel.from_pretrained(translation_model_name)
        
        # Перемещаем модель на нужное устройство
        _translation_model = _translation_model.to(device)
        
        print(f"Модель перевода загружена на {device}!")
    
    return _translation_model, _translation_tokenizer

def _load_vosk_model(model_path=None):
    """
    Ленивая загрузка модели Vosk (Vosk не поддерживает GPU напрямую)
    """
    global _vosk_model
    
    if _vosk_model is None:
        print("Загрузка модели распознавания речи...")
        if model_path is None:
            model_path = str(TRAINED_MODELS_PATH / "vosk-model-ru-0.42")
        
        _vosk_model = Model(model_path)
        print("Модель распознавания речи загружена!")
    
    return _vosk_model

def preload_models(translation_model_name=None, vosk_model_path=None, use_gpu=None):
    """
    Предварительная загрузка всех моделей для ускорения последующих операций
    
    Параметры:
    translation_model_name (str): Путь к модели перевода
    vosk_model_path (str): Путь к модели Vosk
    use_gpu (bool): Использовать GPU для моделей перевода
    """
    print("Предварительная загрузка моделей...")
    _load_translation_model(translation_model_name, use_gpu)
    _load_vosk_model(vosk_model_path)
    print("Все модели загружены и готовы к использованию!")

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

def extract_audio(video_path, output_audio_path):
    """
    Извлекает аудио из видео и сохраняет как моно WAV PCM
    
    Параметры:
    video_path (str): Путь к видеофайлу
    output_audio_path (str): Путь для сохранения аудио
    
    Возвращает:
    bool: Успешность операции
    """
    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        
        # Указываем параметры для создания моно WAV PCM
        audio.write_audiofile(
            output_audio_path,
            codec='pcm_s16le',  # PCM формат
            ffmpeg_params=["-ac", "1"]  # Один канал (моно)
        )
        
        audio.close()
        video.close()
        return True
    except Exception as e:
        print(f"Ошибка при извлечении аудио: {e}")
        return False

def convert_wav_to_bilingual_subtitles(wav_file_path, output_srt_path=None, model_path=None, translation_model_name=None, use_gpu=None):
    """
    Преобразует WAV файл в двуязычные субтитры формата SRT (русский + французский)
    
    Параметры:
    wav_file_path (str): Путь к WAV файлу
    output_srt_path (str): Путь для сохранения SRT файла (опционально)
    model_path (str): Путь к модели Vosk для русского языка
    translation_model_name (str): Путь к модели перевода
    
    Возвращает:
    tuple: (путь к созданному SRT файлу, DataFrame с результатами распознавания и перевода)
    """
    import time
    
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
    wf = wave.open(wav_file_path, "rb")
    
    # Проверяем частоту дискретизации
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Аудиофайл должен быть в формате WAV mono PCM")
        return None, None
    
    # Получаем частоту дискретизации для расчета времени
    frame_rate = wf.getframerate()
    
    # Создаем распознаватель с указанной частотой дискретизации
    recognizer = KaldiRecognizer(vosk_model, frame_rate)
    recognizer.SetWords(True)  # Включаем вывод слов и временных меток
    
    # Открываем файл для записи субтитров в формате SRT
    with open(output_srt_path, "w", encoding="utf-8") as f:
        pass  # Просто создаем пустой файл
    
    # Переменные для отслеживания прогресса и нумерации субтитров
    total_frames = wf.getnframes()
    processed_frames = 0
    subtitle_count = 0
    
    # Создаем список для хранения результатов для DataFrame
    recognition_results = []
    
    # Статистика времени
    total_translation_time = 0
    translation_count = 0
    
    # Читаем аудиофайл по частям и распознаем
    while True:
        data = wf.readframes(FRAME_CHUNK_SIZE)  # Читаем блок данных
        if len(data) == 0:
            break
        
        processed_frames += FRAME_CHUNK_SIZE
        progress = min(100, int(processed_frames / total_frames * 100))
        print(f"Прогресс распознавания: {progress}%", end="\r")
        
        if recognizer.AcceptWaveform(data):
            subtitle_count += 1
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
                    current_frame = processed_frames - FRAME_CHUNK_SIZE
                    start_time = max(0, (current_frame - FRAME_CHUNK_SIZE) / frame_rate)
                    end_time = current_frame / frame_rate
                
                # Сохраняем результат для DataFrame
                recognition_results.append({
                    'id': subtitle_count,
                    'start_time': format_srt_time(start_time),
                    'end_time': format_srt_time(end_time),
                    'russian_text': ru_text,
                    'french_text': fr_text
                })
                
                # Записываем субтитр в SRT формате с французским текстом
                with open(output_srt_path, "a", encoding="utf-8") as f:
                    f.write(f"{subtitle_count}\n")
                    f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
                    f.write(f"{fr_text}\n\n")
    
    # Обрабатываем финальный результат
    final_result = json.loads(recognizer.FinalResult())
    final_ru_text = final_result.get('text', '')
    
    if final_ru_text:
        subtitle_count += 1
        
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
            start_time = (processed_frames - FRAME_CHUNK_SIZE) / frame_rate
            end_time = processed_frames / frame_rate
        
        # Сохраняем финальный результат для DataFrame
        recognition_results.append({
            'id': subtitle_count,
            'start_time': format_srt_time(start_time),
            'end_time': format_srt_time(end_time),
            'russian_text': final_ru_text,
            'french_text': final_fr_text
        })
        
        # Записываем финальный субтитр
        with open(output_srt_path, "a", encoding="utf-8") as f:
            f.write(f"{subtitle_count}\n")
            f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
            f.write(f"{final_fr_text}\n\n")
    
    print(f"\nРаспознавание и перевод завершены. Субтитры сохранены в файл {output_srt_path}")
    
    # Выводим статистику времени
    if translation_count > 0:
        avg_translation_time = total_translation_time / translation_count
        print(f"Статистика перевода:")
        print(f"  Всего переводов: {translation_count}")
        print(f"  Общее время перевода: {total_translation_time:.2f} сек")
        print(f"  Среднее время на перевод: {avg_translation_time:.3f} сек")
    
    # Создаем DataFrame с результатами
    df_results = pd.DataFrame(recognition_results)
    
    return output_srt_path, df_results

def add_subtitles_to_video(video_path, srt_path, output_video_path, ffmpeg_path=None):
    """
    Добавляет субтитры к видео с помощью FFmpeg
    
    Параметры:
    video_path (str): Путь к исходному видео
    srt_path (str): Путь к файлу субтитров
    output_video_path (str): Путь для сохранения результата
    ffmpeg_path (str): Путь к исполняемому файлу FFmpeg
    
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
        print(f"Ошибка: видеофайл не найден: {video_path}")
        return False
    
    if not os.path.exists(srt_path):
        print(f"Ошибка: файл субтитров не найден: {srt_path}")
        return False
    
    # Создаём директорию для выходного файла, если её нет
    output_dir = os.path.dirname(output_video_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Правильное экранирование пути к файлу субтитров для Windows
    # Заменяем обратные слеши на прямые и экранируем двоеточие
    escaped_srt_path = srt_path.replace('\\', '/').replace(':', '\\\\:')
    
    # Создаем команду с правильным экранированием
    vf_filter = f'subtitles={escaped_srt_path}:force_style=\'FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3\''
    
    command = [
        ffmpeg_path,
        '-i', video_path,
        '-vf', vf_filter,
        '-c:a', 'copy',
        output_video_path,
        '-y'  # Перезаписать выходной файл, если он существует
    ]
    
    try:
        print(f"Выполняем команду FFmpeg: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Субтитры успешно добавлены. Результат сохранен в {output_video_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при добавлении субтитров: {e}")
        print(f"Команда, которая вызвала ошибку: {' '.join(command)}")
        return False