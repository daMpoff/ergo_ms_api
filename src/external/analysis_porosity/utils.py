import os
import shutil
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def save_uploaded_image(image_file, analysis_uuid):
    """
    Сохраняет загруженное изображение для анализа
    
    Args:
        image_file: Загруженный файл изображения
        analysis_uuid: UUID анализа
    
    Returns:
        str: Путь к сохраненному файлу
    """
    try:
        # Создаем директорию если её нет
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'porosity_analysis', 'initial_photo')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Формируем путь к файлу
        file_path = os.path.join(upload_dir, f"{analysis_uuid}.png")
        
        # Открываем изображение с помощью PIL
        with Image.open(image_file) as img:
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Сохраняем как PNG
            img.save(file_path, 'PNG')
        
        logger.info(f"Изображение сохранено: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {str(e)}")
        raise


def cleanup_analysis_files(analysis):
    """
    Удаляет файлы анализа
    
    Args:
        analysis: Объект PorosityAnalysis
    """
    try:
        # Удаляем исходное изображение
        if os.path.exists(analysis.original_image_path):
            os.remove(analysis.original_image_path)
            logger.info(f"Удалено исходное изображение: {analysis.original_image_path}")
        
        # Удаляем директорию результатов
        if os.path.exists(analysis.results_directory):
            shutil.rmtree(analysis.results_directory)
            logger.info(f"Удалена директория результатов: {analysis.results_directory}")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении файлов анализа {analysis.id}: {str(e)}")


def get_analysis_results_files(analysis):
    """
    Получает список файлов результатов анализа
    
    Args:
        analysis: Объект PorosityAnalysis
    
    Returns:
        list: Список путей к файлам результатов
    """
    if not os.path.exists(analysis.results_directory):
        return []
    
    files = []
    for root, dirs, filenames in os.walk(analysis.results_directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files.append(file_path)
    
    return files


def validate_image_file(file_path):
    """
    Проверяет валидность файла изображения
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        bool: True если файл валиден
    """
    try:
        with Image.open(file_path) as img:
            # Проверяем что это изображение
            img.verify()
        return True
    except Exception as e:
        logger.error(f"Файл {file_path} не является валидным изображением: {str(e)}")
        return False


def get_file_size_mb(file_path):
    """
    Получает размер файла в мегабайтах
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        float: Размер файла в МБ
    """
    if os.path.exists(file_path):
        return os.path.getsize(file_path) / (1024 * 1024)
    return 0.0


def create_analysis_summary(analysis):
    """
    Создает краткое описание результатов анализа
    
    Args:
        analysis: Объект PorosityAnalysis
    
    Returns:
        dict: Словарь с кратким описанием
    """
    summary = {
        'id': analysis.id,
        'name': analysis.name,
        'status': analysis.status,
        'created_at': analysis.created_at.isoformat(),
        'porosity_percentage': analysis.porosity_percentage,
        'number_of_pores': analysis.number_of_pores,
        'average_pore_size': analysis.average_pore_size,
        'file_size_mb': get_file_size_mb(analysis.original_image_path),
        'has_results': os.path.exists(analysis.results_directory),
    }
    
    if analysis.status == 'failed':
        summary['error_message'] = analysis.error_message
    
    return summary 