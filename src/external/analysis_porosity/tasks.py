"""
Задачи Celery для фоновой обработки анализов пористости
"""

import os
import logging
import traceback
from celery import shared_task
from django.conf import settings
from django.core.files import File
from django.utils import timezone

# Настройка Matplotlib для работы без GUI (для фоновых процессов)
import matplotlib
matplotlib.use('Agg')

from src.external.analysis_porosity.models import PorosityAnalysis, PorosityResult, AnalysisFile
from src.external.analysis_porosity.square_porosity.porosity_analyzer import PorosityAnalyzer
from src.external.analysis_porosity.square_porosity.config import FILES, MESSAGES

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_porosity_analysis(self, analysis_id):
    """
    Фоновая задача для обработки анализа пористости
    
    Args:
        analysis_id (int): ID анализа для обработки
    """
    try:
        # Получаем анализ
        analysis = PorosityAnalysis.objects.get(id=analysis_id)
        
        # Обновляем статус на "обработка"
        analysis.status = 'processing'
        analysis.save()
        
        logger.info(f"Начинаем обработку анализа {analysis_id}: {analysis.title}")
        
        # Получаем файл изображения
        image_file = analysis.original_image
        if not image_file:
            raise ValueError("Файл изображения не найден")
        
        # Создаем папку для результатов в media
        output_dir = os.path.join(settings.MEDIA_ROOT, 'porosity_analysis', str(analysis_id))
        os.makedirs(output_dir, exist_ok=True)
        
        # Убеждаемся, что используем абсолютный путь
        output_dir = os.path.abspath(output_dir)
        
        logger.info(f"Создана директория для результатов: {output_dir}")
        logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        logger.info(f"Абсолютный путь: {os.path.abspath(output_dir)}")
        
        # Инициализируем анализатор
        analyzer = PorosityAnalyzer()
        
        # Запускаем анализ
        logger.info(f"Запуск анализатора для файла: {image_file.name}")
        
        # Получаем путь к файлу
        image_path = image_file.path
        
        logger.info(f"Путь к изображению: {image_path}")
        logger.info(f"Текущая рабочая директория: {os.getcwd()}")
        logger.info(f"Переменная окружения TMPDIR: {os.environ.get('TMPDIR', 'Не установлена')}")
        logger.info(f"Переменная окружения TEMP: {os.environ.get('TEMP', 'Не установлена')}")
        
        # Выполняем анализ
        try:
            results = analyzer.analyze_porosity(
                image_path,
                analysis.scale_value,
                output_dir
            )
            
            if results:
                # Сохраняем результаты в базу данных
                save_analysis_results(analysis, results, output_dir)
                
                # Обновляем статус на "завершено"
                analysis.status = 'completed'
                analysis.processed_at = timezone.now()
                analysis.save()
                
                logger.info(f"Анализ {analysis_id} успешно завершен")
                
                return {
                    'status': 'success',
                    'analysis_id': analysis_id,
                    'message': 'Анализ успешно завершен'
                }
            else:
                raise ValueError("Анализ не вернул результатов")
                
        except Exception as analysis_error:
            logger.error(f"Ошибка при выполнении анализа {analysis_id}: {str(analysis_error)}")
            analysis.status = 'error'
            analysis.error_message = f"Ошибка анализа: {str(analysis_error)}"
            analysis.save()
            
            return {
                'status': 'error',
                'analysis_id': analysis_id,
                'message': f'Ошибка анализа: {str(analysis_error)}'
            }
        
    except PorosityAnalysis.DoesNotExist:
        error_msg = f"Анализ с ID {analysis_id} не найден"
        logger.error(error_msg)
        update_analysis_status(analysis_id, 'error', error_msg)
        return {
            'status': 'error',
            'analysis_id': analysis_id,
            'message': error_msg
        }
        
    except Exception as e:
        error_msg = f"Ошибка обработки анализа {analysis_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_analysis_status(analysis_id, 'error', error_msg)
        return {
            'status': 'error',
            'analysis_id': analysis_id,
            'message': error_msg
        }


def save_analysis_results(analysis, results, output_dir):
    """
    Сохраняет результаты анализа в базу данных
    
    Args:
        analysis (PorosityAnalysis): Объект анализа
        results (dict): Результаты анализа
        output_dir (str): Путь к папке с результатами
    """
    try:
        # Создаем или обновляем результат анализа
        result, created = PorosityResult.objects.get_or_create(
            analysis=analysis,
            defaults={
                'porosity_percentage': results.get('porosity_percentage', 0.0),
                'relative_pore_area': results.get('relative_pore_area', 0.0),
                'number_of_pores': results.get('number_of_pores', 0),
                'mean_pore_size_microns': results.get('mean_pore_size_microns', 0.0),
                'median_pore_size_microns': results.get('median_pore_size_microns', 0.0),
                'mean_pore_diameter_microns': results.get('mean_pore_diameter_microns', 0.0),
                'median_pore_diameter_microns': results.get('median_pore_diameter_microns', 0.0),
                'pixels_per_micron': results.get('pixels_per_micron', 0.0),
                'scale_region_x': results.get('scale_region_x', 0),
                'scale_region_y': results.get('scale_region_y', 0),
                'scale_region_width': results.get('scale_region_width', 0),
                'scale_region_height': results.get('scale_region_height', 0),
                'total_pixels': results.get('total_pixels', 0),
                'scale_excluded_pixels': results.get('scale_excluded_pixels', 0),
                'lines_excluded_pixels': results.get('lines_excluded_pixels', 0),
                'anomalies_excluded_pixels': results.get('anomalies_excluded_pixels', 0),
                'total_excluded_pixels': results.get('total_excluded_pixels', 0),
                'extended_metrics': results.get('extended_metrics', {})
            }
        )
        
        if not created:
            # Обновляем существующий результат
            result.porosity_percentage = results.get('porosity_percentage', 0.0)
            result.relative_pore_area = results.get('relative_pore_area', 0.0)
            result.number_of_pores = results.get('number_of_pores', 0)
            result.mean_pore_size_microns = results.get('mean_pore_size_microns', 0.0)
            result.median_pore_size_microns = results.get('median_pore_size_microns', 0.0)
            result.mean_pore_diameter_microns = results.get('mean_pore_diameter_microns', 0.0)
            result.median_pore_diameter_microns = results.get('median_pore_diameter_microns', 0.0)
            result.pixels_per_micron = results.get('pixels_per_micron', 0.0)
            result.scale_region_x = results.get('scale_region_x', 0)
            result.scale_region_y = results.get('scale_region_y', 0)
            result.scale_region_width = results.get('scale_region_width', 0)
            result.scale_region_height = results.get('scale_region_height', 0)
            result.total_pixels = results.get('total_pixels', 0)
            result.scale_excluded_pixels = results.get('scale_excluded_pixels', 0)
            result.lines_excluded_pixels = results.get('lines_excluded_pixels', 0)
            result.anomalies_excluded_pixels = results.get('anomalies_excluded_pixels', 0)
            result.total_excluded_pixels = results.get('total_excluded_pixels', 0)
            result.extended_metrics = results.get('extended_metrics', {})
            result.save()
        
        # Сохраняем файлы результатов
        save_result_files(analysis, output_dir)
        
        logger.info(f"Результаты анализа {analysis.id} сохранены в базу данных")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов анализа {analysis.id}: {str(e)}")
        raise


def save_result_files(analysis, output_dir):
    """
    Сохраняет файлы результатов анализа в базу данных
    
    Args:
        analysis (PorosityAnalysis): Объект анализа
        output_dir (str): Путь к папке с результатами
    """
    try:
        # Словарь соответствия имен файлов и их типов
        file_type_mapping = {
            'scale_bar.png': 'scale_bar',
            'image_with_scale_bar.png': 'scale_region',
            'analysis_stages.png': 'contrast_stages',
            'excluded_areas.png': 'excluded_areas',
            'texture_clusters.png': 'texture_clusters',
            'mask_result.png': 'mask_result',
            'overlay_result.png': 'overlay',
            'pore_size_distribution.png': 'pore_size_distribution',
            'interpore_distances.png': 'interpore_distances',
            'pore_orientation_rose.png': 'pore_orientation_rose',
            'pore_orientation_histogram.png': 'pore_orientation_histogram',
            'pore_shapes_analysis.png': 'pore_shapes_analysis',
            'circularity_distribution.png': 'circularity_distribution',
            'ellipticity_vs_area.png': 'ellipticity_vs_area'
        }
        
        # Проходим по всем файлам в директории
        for filename in os.listdir(output_dir):
            if filename in file_type_mapping:
                file_path = os.path.join(output_dir, filename)
                file_type = file_type_mapping[filename]
                
                # Создаем или обновляем запись файла
                with open(file_path, 'rb') as f:
                    analysis_file, created = AnalysisFile.objects.get_or_create(
                        analysis=analysis,
                        file_type=file_type,
                        defaults={
                            'filename': filename,
                            'description': f"Результат анализа: {file_type}"
                        }
                    )
                    
                    # Сохраняем файл в media
                    analysis_file.file.save(f"{analysis.id}_{filename}", File(f), save=True)
                    
                    logger.info(f"Сохранен файл {filename} для анализа {analysis.id}")
        
        logger.info(f"Все файлы результатов для анализа {analysis.id} сохранены")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении файлов результатов анализа {analysis.id}: {str(e)}")
        raise


def update_analysis_status(analysis_id, status, error_message=None):
    """
    Обновляет статус анализа
    
    Args:
        analysis_id (int): ID анализа
        status (str): Новый статус
        error_message (str): Сообщение об ошибке
    """
    try:
        analysis = PorosityAnalysis.objects.get(id=analysis_id)
        analysis.status = status
        
        if error_message:
            analysis.error_message = error_message
        
        if status == 'completed':
            analysis.completed_at = timezone.now()
        
        analysis.save()
        
        logger.info(f"Статус анализа {analysis_id} обновлен на '{status}'")
        
    except PorosityAnalysis.DoesNotExist:
        logger.error(f"Анализ {analysis_id} не найден для обновления статуса")
    except Exception as e:
        logger.error(f"Ошибка обновления статуса анализа {analysis_id}: {str(e)}")


@shared_task
def cleanup_old_analyses():
    """
    Задача для очистки старых анализов и файлов
    """
    try:
        from datetime import timedelta
        
        # Удаляем анализы старше 30 дней
        cutoff_date = timezone.now() - timedelta(days=30)
        old_analyses = PorosityAnalysis.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'error']
        )
        
        count = old_analyses.count()
        old_analyses.delete()
        
        logger.info(f"Удалено {count} старых анализов")
        
        return {
            'status': 'success',
            'deleted_count': count
        }
        
    except Exception as e:
        logger.error(f"Ошибка очистки старых анализов: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        } 