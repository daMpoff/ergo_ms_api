import os
import uuid
import logging
import time
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
    generate_tts_from_subtitles,
    combine_tts_audio_segments,
    add_tts_audio_to_video,
    TRAINED_MODELS_PATH,
    FFMPEG_PATH
)
from src.modules.video_analysis.utils import (
    log_task_start, 
    log_task_complete, 
    log_task_error,
    log_file_operation,
    log_performance_metric
)

# Получаем логгер для модуля
logger = logging.getLogger('video_analysis')

@shared_task(bind=True)
def translate_video_analysis(self, video_name, user_id=1, use_gpu=None, analysis_uuid=None, title=None):
    """
    Основная Celery задача: перевод видео, создание анализа в БД, сохранение всех файлов и сегментов.
    Все папки внутри media/video_analysis/.
    """
    start_time = time.time()
    
    # Логируем начало задачи
    log_task_start('translate_video_analysis', video_name=video_name, user_id=user_id, use_gpu=use_gpu)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    from src.config.settings.static import MEDIA_ROOT

    try:
        # --- Папки ---
        video_analysis_root = Path(MEDIA_ROOT) / 'video_analysis'
        initial_video_dir = Path(video_analysis_root) / 'initial_video'
        results_root = Path(video_analysis_root) / 'results'

        # --- UUID анализа ---
        if analysis_uuid is None:
            logger.error("UUID анализа не передан, что недопустимо в новой логике")
            raise ValueError("UUID анализа обязателен")
        results_path = Path(results_root) / analysis_uuid
        results_path.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"video_analysis_root = {video_analysis_root}")
        logger.debug(f"initial_video_dir = {initial_video_dir}")
        logger.debug(f"results_root = {results_root}")
        logger.debug(f"analysis_uuid = {analysis_uuid}")
        logger.debug(f"results_path = {results_path}")

        # --- Исходное видео ---
        video_path = Path(initial_video_dir) / video_name
        if not os.path.exists(video_path):
            raise Exception(f'Файл {video_path} не найден!')
        
        # Для UUID файлов base_name будет UUID анализа
        base_name = os.path.splitext(video_name)[0]
        # Проверяем, что base_name соответствует analysis_uuid
        if base_name != analysis_uuid:
            logger.warning(f"base_name ({base_name}) не совпадает с analysis_uuid ({analysis_uuid}). Используем analysis_uuid.")
            base_name = analysis_uuid
        
        logger.debug(f"video_path = {video_path}")
        logger.debug(f"base_name = {base_name}")

        # --- Создаём или получаем VideoAnalysis ---
        try:
            user = User.objects.get(id=user_id)
            logger.info(f"Пользователь найден - {user.username} (ID: {user.id})")
        except User.DoesNotExist:
            user = User.objects.first()
            if not user:
                raise Exception(f'Пользователь с ID {user_id} не найден и нет других пользователей в системе')
            logger.warning(f"Пользователь с ID {user_id} не найден, используется первый пользователь - {user.username} (ID: {user.id})")

        from src.modules.video_analysis.utils import log_model_operation
        # Ищем существующий анализ (должен быть создан во views)
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_uuid, user=user)
            # Обновляем статус на processing
            analysis.update_status('processing')
            log_model_operation('update', 'VideoAnalysis', analysis_uuid=analysis_uuid, status='processing')
            logger.info(f"Найден анализ с ID {analysis.id}, статус обновлен на 'processing'")
        except VideoAnalysis.DoesNotExist:
            logger.error(f"Анализ с UUID {analysis_uuid} не найден для пользователя {user.id}")
            raise ValueError(f"Анализ с UUID {analysis_uuid} не найден")
        
        logger.info(f"Создан анализ с ID {analysis.id}")
        logger.info(f"Настройки субтитров анализа: lines={analysis.subtitle_lines_count}, size={analysis.subtitle_font_size}, "
                   f"font_color={analysis.subtitle_font_color}, bg_color={analysis.subtitle_background_color}, "
                   f"transparent={analysis.subtitle_background_transparent}")

        # --- Пути для результатов ---
        temp_audio_path = Path(results_path) / f'{base_name}_temp_audio.wav'
        temp_srt_path = Path(results_path) / f'{base_name}_bilingual.srt'
        output_video_path = Path(results_path) / f'{base_name}_with_bilingual_subtitles.mp4'
        
        logger.debug(f"temp_audio_path = {temp_audio_path}")
        logger.debug(f"temp_srt_path = {temp_srt_path}")
        logger.debug(f"output_video_path = {output_video_path}")

        # --- Извлечение аудио ---
        self.update_state(state='EXTRACTING_AUDIO', meta={'progress': 10})
        
        logger.debug(f"video_path = {video_path} (тип: {type(video_path)})")
        logger.debug(f"temp_audio_path = {temp_audio_path} (тип: {type(temp_audio_path)})")
        
        # Логируем операцию извлечения аудио
        log_file_operation('extract_audio', str(video_path), output_path=str(temp_audio_path))
        
        if not extract_audio(str(video_path), str(temp_audio_path)):
            analysis.status = 'failed'
            analysis.error_message = 'Ошибка при извлечении аудио'
            analysis.save()
            return {'status': 'error', 'message': analysis.error_message}

        # --- Загрузка моделей ---
        self.update_state(state='LOADING_MODELS', meta={'progress': 20})
        
        opus_model_path = str(Path(TRAINED_MODELS_PATH) / "opus-mt-ru-fr")
        vosk_model_path = str(Path(TRAINED_MODELS_PATH) / "vosk-model-ru-0.42")
        
        logger.debug(f"opus_model_path = {opus_model_path}")
        logger.debug(f"vosk_model_path = {vosk_model_path}")
        logger.debug(f"use_gpu = {use_gpu} (тип: {type(use_gpu)})")
        
        # Логируем загрузку моделей
        log_file_operation('load_models', str(opus_model_path), 
                          vosk_model=str(vosk_model_path), 
                          use_gpu=use_gpu)
        
        preload_models(
            opus_model_path,
            vosk_model_path,
            use_gpu
        )

        # --- Распознавание и перевод ---
        self.update_state(state='RECOGNIZING_SPEECH', meta={'progress': 30})
        
        temp_audio_path_str = str(temp_audio_path)
        temp_srt_path_str = str(temp_srt_path)
        
        logger.debug(f"temp_audio_path_str = {temp_audio_path_str}")
        logger.debug(f"temp_srt_path_str = {temp_srt_path_str}")
        
        # Логируем начало распознавания речи
        log_file_operation('speech_recognition', str(temp_audio_path), 
                          output_srt=str(temp_srt_path), 
                          use_gpu=use_gpu)
        
        srt_path, df_subtitles = convert_wav_to_bilingual_subtitles(
            temp_audio_path_str,
            temp_srt_path_str,
            use_gpu=use_gpu,
            subtitle_lines_count=analysis.subtitle_lines_count,
            video_path=str(video_path),
            font_size=analysis.subtitle_font_size
        )
        if not srt_path or df_subtitles is None:
            analysis.status = 'failed'
            analysis.error_message = 'Ошибка при распознавании речи'
            analysis.save()
            return {'status': 'error', 'message': analysis.error_message}

        # --- Сохраняем сегменты субтитров ---
        self.update_state(state='SAVING_SEGMENTS', meta={'progress': 60})
        
        logger.debug(f"df_subtitles.shape = {df_subtitles.shape}")
        logger.debug(f"df_subtitles.columns = {list(df_subtitles.columns)}")
        
        # Удаляем старые сегменты, если они есть
        old_segments_count = analysis.clear_subtitle_segments()
        if old_segments_count > 0:
            logger.info(f"Удалено {old_segments_count} старых сегментов")
        
        # Создаем новые сегменты
        segments_created = 0
        for _, row in df_subtitles.iterrows():
            try:
                logger.debug(f"Создаю сегмент {row['id']} - {row['start_time']} -> {row['end_time']}")
                
                # Логируем создание сегмента
                log_model_operation('create', 'SubtitleSegment', 
                                   segment_id=row['id'], 
                                   analysis_uuid=analysis_uuid,
                                   start_time=row['start_time'],
                                   end_time=row['end_time'])
                
                analysis.add_subtitle_segment(
                    segment_number=row['id'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    russian_text=row['russian_text'],
                    french_text=row['french_text']
                )
                segments_created += 1
            except Exception as e:
                logger.error(f"Ошибка при создании сегмента {row['id']}: {e}")
                continue
        
        logger.info(f"Создано {segments_created} сегментов субтитров для анализа {analysis_uuid}")
        
        # Проверяем, что сегменты действительно созданы
        final_segments_count = analysis.get_subtitle_segments_count()
        logger.info(f"Всего сегментов в БД для анализа {analysis_uuid}: {final_segments_count}")

        # --- Генерация TTS озвучки (если включена) ---
        tts_audio_path = None
        if analysis.tts_enabled:
            self.update_state(state='GENERATING_TTS', meta={'progress': 70})
            
            logger.info("Генерация TTS озвучки...")
            
            # Создаем директорию для TTS файлов
            tts_dir = results_path / 'tts'
            tts_dir.mkdir(exist_ok=True)
            
            # Генерируем TTS из субтитров
            subtitle_segments_data = analysis.get_subtitle_segments_data()
            if subtitle_segments_data:
                # Определяем спикера в зависимости от языка
                if analysis.tts_language == 'ru':
                    speaker = 'v3_1_ru'  # Стандартный русский голос
                elif analysis.tts_language == 'fr':
                    speaker = 'v3_fr'  # Французский голос (если доступен)
                elif analysis.tts_language == 'en':
                    speaker = 'v3_en'  # Английский голос
                else:
                    speaker = 'v3_1_ru'  # По умолчанию русский
                
                # Генерируем аудио сегменты
                audio_segments = generate_tts_from_subtitles(
                    subtitle_segments_data,
                    str(tts_dir),
                    language=analysis.tts_language,
                    speaker=speaker,
                    volume=analysis.tts_volume
                )
                
                if audio_segments:
                    # Объединяем сегменты в один файл
                    tts_combined_path = results_path / f'{base_name}_tts_audio.wav'
                    
                    if combine_tts_audio_segments(audio_segments, str(tts_combined_path), duration):
                        tts_audio_path = str(tts_combined_path)
                        
                        # Сохраняем путь к TTS файлу в модели
                        analysis.tts_audio_file = f'video_analysis/results/{analysis_uuid}/{base_name}_tts_audio.wav'
                        
                        logger.info(f"TTS озвучка создана: {tts_audio_path}")
                    else:
                        logger.warning("Не удалось объединить TTS аудио сегменты")
                else:
                    logger.warning("Не удалось сгенерировать TTS аудио сегменты")
            else:
                logger.warning("Нет данных субтитров для генерации TTS")

        # --- Добавление субтитров к видео ---
        self.update_state(state='ADDING_SUBTITLES', meta={'progress': 80})
        
        video_path_abs = os.path.abspath(str(video_path))
        srt_path_abs = os.path.abspath(str(srt_path))
        output_video_path_abs = os.path.abspath(str(output_video_path))
        
        logger.debug(f"video_path_abs = {video_path_abs}")
        logger.debug(f"srt_path_abs = {srt_path_abs}")
        logger.debug(f"output_video_path_abs = {output_video_path_abs}")
        # Логируем операцию добавления субтитров
        log_file_operation('add_subtitles', str(video_path_abs), 
                          srt_path=str(srt_path_abs), 
                          output_path=str(output_video_path_abs))
        
        # Если есть TTS аудио, сначала создаем видео с субтитрами, затем добавляем TTS
        if tts_audio_path:
            # Создаем временное видео с субтитрами
            temp_video_with_subs = results_path / f'{base_name}_temp_with_subs.mp4'
            
            success = add_subtitles_to_video(
                video_path_abs,
                srt_path_abs,
                str(temp_video_with_subs),
                str(FFMPEG_PATH),
                subtitle_lines_count=analysis.subtitle_lines_count,
                subtitle_font_size=analysis.subtitle_font_size,
                subtitle_font_color=analysis.subtitle_font_color,
                subtitle_background_color=analysis.subtitle_background_color,
                subtitle_background_transparent=analysis.subtitle_background_transparent
            )
            
            if not success:
                analysis.status = 'failed'
                analysis.error_message = 'Ошибка при добавлении субтитров'
                analysis.save()
                return {'status': 'error', 'message': analysis.error_message}
            
            # Добавляем TTS аудио к видео с субтитрами
            self.update_state(state='ADDING_TTS_AUDIO', meta={'progress': 90})
            
            success = add_tts_audio_to_video(
                str(temp_video_with_subs),
                tts_audio_path,
                output_video_path_abs,
                str(FFMPEG_PATH),
                volume=analysis.tts_volume
            )
            
            # Удаляем временный файл
            try:
                temp_video_with_subs.unlink()
            except:
                pass
            
            if not success:
                analysis.status = 'failed'
                analysis.error_message = 'Ошибка при добавлении TTS аудио'
                analysis.save()
                return {'status': 'error', 'message': analysis.error_message}
        else:
            # Обычное добавление субтитров без TTS
            success = add_subtitles_to_video(
                video_path_abs,
                srt_path_abs,
                output_video_path_abs,
                str(FFMPEG_PATH),
                subtitle_lines_count=analysis.subtitle_lines_count,
                subtitle_font_size=analysis.subtitle_font_size,
                subtitle_font_color=analysis.subtitle_font_color,
                subtitle_background_color=analysis.subtitle_background_color,
                subtitle_background_transparent=analysis.subtitle_background_transparent
            )
            if not success:
                analysis.status = 'failed'
                analysis.error_message = 'Ошибка при добавлении субтитров'
                analysis.save()
                return {'status': 'error', 'message': analysis.error_message}

        # --- Сохраняем пути к файлам в модели (файлы остаются в results папке) ---
        audio_file_path = f'video_analysis/results/{analysis_uuid}/{base_name}_temp_audio.wav'
        subtitles_file_path = f'video_analysis/results/{analysis_uuid}/{base_name}_bilingual.srt'
        output_video_file_path = f'video_analysis/results/{analysis_uuid}/{base_name}_with_bilingual_subtitles.mp4'
        
        logger.debug(f"audio_file_path = {audio_file_path}")
        logger.debug(f"subtitles_file_path = {subtitles_file_path}")
        logger.debug(f"output_video_file_path = {output_video_file_path}")
        
        analysis.audio_file = audio_file_path
        analysis.subtitles_file = subtitles_file_path
        analysis.output_video = output_video_file_path

        # --- Длительность видео ---
        try:
            # Логируем получение длительности видео
            log_file_operation('get_duration', str(video_path_abs))
            
            video = VideoFileClip(video_path_abs)
            duration = video.duration
            video.close()
            
            logger.debug(f"duration = {duration} (тип: {type(duration)})")
        except Exception as e:
            logger.warning(f"Ошибка при получении длительности видео: {e}")
            duration = 0

        # --- Обновляем статус анализа ---
        subtitle_count = len(df_subtitles)
        
        logger.debug(f"subtitle_count = {subtitle_count} (тип: {type(subtitle_count)})")
        logger.debug(f"duration = {duration} (тип: {type(duration)})")
        
        # Логируем обновление статуса анализа
        log_model_operation('update', 'VideoAnalysis', 
                           analysis_uuid=analysis_uuid, 
                           status='completed', 
                           subtitle_count=subtitle_count,
                           duration=duration)
        
        analysis.status = 'completed'
        analysis.subtitle_count = subtitle_count
        analysis.duration = duration
        analysis.completed_at = timezone.now()
        analysis.save()

        # --- Временные файлы остаются в папке results ---
        # Аудио файл сохраняется для возможного повторного использования

        result = {
            'status': 'completed',
            'analysis_uuid': analysis_uuid,
            'video_name': video_name,
            'srt_file': str(temp_srt_path),
            'output_video': str(output_video_path),
            'subtitle_count': len(df_subtitles),
            'results_dir': str(results_path),
            'db_id': str(analysis.id)
        }
        
        # Логируем успешное завершение задачи
        duration = time.time() - start_time
        log_task_complete('translate_video_analysis', duration, 
                         analysis_uuid=analysis_uuid, 
                         subtitle_count=len(df_subtitles),
                         video_name=video_name)
        log_performance_metric('total_processing_time', duration)
        
        logger.info(f"Задача успешно завершена. Возвращаемый результат: {result}")
        
        return result
    except Exception as e:
        import traceback
        
        # Получаем полный стек ошибки
        error_traceback = traceback.format_exc()
        error_message = f"Ошибка: {str(e)}\n\nПолный стек ошибки:\n{error_traceback}"
        
        # Логируем ошибку задачи
        duration = time.time() - start_time
        log_task_error('translate_video_analysis', e, 
                      video_name=video_name, 
                      user_id=user_id, 
                      duration=duration)
        
        logger.error(f"Ошибка в задаче translate_video_analysis: {error_message}")
        
        # Если анализ уже создан — обновляем статус
        try:
            analysis.status = 'failed'
            analysis.error_message = error_message
            analysis.save()
            logger.info(f"Статус анализа {analysis_uuid} обновлен на 'failed'")
        except Exception as save_error:
            logger.error(f"Не удалось обновить статус анализа {analysis_uuid}: {save_error}")
        
        return {'status': 'error', 'message': error_message}