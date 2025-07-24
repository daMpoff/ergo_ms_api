import os
import uuid
from pathlib import Path

from celery import shared_task

from django.utils import timezone
from django.core.files import File
from moviepy.editor import VideoFileClip

from src.modules.video_analysis.models import VideoAnalysis, SubtitleSegment
from src.modules.video_analysis.scripts import (
    extract_audio,
    convert_wav_to_bilingual_subtitles,
    add_subtitles_to_video,
    preload_models,
    TRAINED_MODELS_PATH,
    FFMPEG_PATH
)

@shared_task(bind=True)
def translate_video_analysis(self, video_name, user_id=1):
    """
    Основная Celery задача: перевод видео, создание анализа в БД, сохранение всех файлов и сегментов.
    Все папки внутри media/video_analysis/.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    from src.config.settings.static import MEDIA_ROOT

    try:
        # --- Папки ---
        video_analysis_root = Path(MEDIA_ROOT) / 'video_analysis'
        initial_video_dir = video_analysis_root / 'initial_video'
        results_root = video_analysis_root / 'results'

        # --- UUID анализа ---
        analysis_uuid = str(uuid.uuid4())
        results_path = results_root / analysis_uuid
        results_path.mkdir(parents=True, exist_ok=True)

        # --- Исходное видео ---
        video_path = initial_video_dir / video_name
        if not os.path.exists(video_path):
            raise Exception(f'Файл {video_path} не найден!')
        base_name = os.path.splitext(video_name)[0]

        # --- Создаём VideoAnalysis ---
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Если пользователь не найден, создаем его или берем первого
            user = User.objects.first()
            if not user:
                raise Exception(f'Пользователь с ID {user_id} не найден и нет других пользователей в системе')
        
        analysis = VideoAnalysis.objects.create(
            id=analysis_uuid,
            user=user,
            title=base_name,
            description=f'Автоматический анализ для файла {video_name}',
            original_video=f'video_analysis/initial_video/{video_name}',
            status='processing',
        )

        # --- Пути для результатов ---
        temp_audio_path = results_path / f'{base_name}_temp_audio.wav'
        temp_srt_path = results_path / f'{base_name}_bilingual.srt'
        output_video_path = results_path / f'{base_name}_with_bilingual_subtitles.mp4'

        # --- Извлечение аудио ---
        self.update_state(state='EXTRACTING_AUDIO', meta={'progress': 10})
        if not extract_audio(str(video_path), str(temp_audio_path)):
            analysis.status = 'failed'
            analysis.error_message = 'Ошибка при извлечении аудио'
            analysis.save()
            return {'status': 'error', 'message': analysis.error_message}

        # --- Загрузка моделей ---
        self.update_state(state='LOADING_MODELS', meta={'progress': 20})
        preload_models(
            str(TRAINED_MODELS_PATH / "opus-mt-ru-fr"),
            str(TRAINED_MODELS_PATH / "vosk-model-ru-0.42")
        )

        # --- Распознавание и перевод ---
        self.update_state(state='RECOGNIZING_SPEECH', meta={'progress': 30})
        srt_path, df_subtitles = convert_wav_to_bilingual_subtitles(
            str(temp_audio_path),
            str(temp_srt_path)
        )
        if not srt_path or df_subtitles is None:
            analysis.status = 'failed'
            analysis.error_message = 'Ошибка при распознавании речи'
            analysis.save()
            return {'status': 'error', 'message': analysis.error_message}

        # --- Сохраняем сегменты субтитров ---
        analysis.subtitle_segments.all().delete()
        for _, row in df_subtitles.iterrows():
            SubtitleSegment.objects.create(
                video_analysis=analysis,
                segment_number=row['id'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                russian_text=row['russian_text'],
                french_text=row['french_text']
            )

        # --- Добавление субтитров к видео ---
        self.update_state(state='ADDING_SUBTITLES', meta={'progress': 80})
        video_path_abs = os.path.abspath(str(video_path))
        srt_path_abs = os.path.abspath(str(srt_path))
        output_video_path_abs = os.path.abspath(str(output_video_path))
        success = add_subtitles_to_video(
            video_path_abs,
            srt_path_abs,
            output_video_path_abs,
            str(FFMPEG_PATH)
        )
        if not success:
            analysis.status = 'failed'
            analysis.error_message = 'Ошибка при добавлении субтитров'
            analysis.save()
            return {'status': 'error', 'message': analysis.error_message}

        # --- Сохраняем файлы в модель ---
        with open(temp_audio_path, 'rb') as f:
            analysis.audio_file.save(f'audio_{analysis_uuid}.wav', File(f), save=False)
        with open(temp_srt_path, 'rb') as f:
            analysis.subtitles_file.save(f'subtitles_{analysis_uuid}.srt', File(f), save=False)
        with open(output_video_path, 'rb') as f:
            analysis.output_video.save(f'output_{analysis_uuid}.mp4', File(f), save=False)

        # --- Длительность видео ---
        video = VideoFileClip(video_path_abs)
        duration = video.duration
        video.close()

        # --- Обновляем статус анализа ---
        analysis.status = 'completed'
        analysis.subtitle_count = len(df_subtitles)
        analysis.duration = duration
        analysis.completed_at = timezone.now()
        analysis.save()

        # --- Удаляем временные файлы ---
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

        return {
            'status': 'completed',
            'analysis_uuid': analysis_uuid,
            'video_name': video_name,
            'srt_file': str(temp_srt_path),
            'output_video': str(output_video_path),
            'subtitle_count': len(df_subtitles),
            'results_dir': str(results_path),
            'db_id': str(analysis.id)
        }
    except Exception as e:
        # Если анализ уже создан — обновляем статус
        try:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
        except Exception:
            pass
        return {'status': 'error', 'message': str(e)}