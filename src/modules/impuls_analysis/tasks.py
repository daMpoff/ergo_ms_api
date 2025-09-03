"""
Задачи Celery для модуля анализа импульса.
Обработка Excel файлов, анализ данных и генерация протоколов.
"""

import logging
import os
import zipfile
from io import BytesIO
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import ImpulsAnalysis, ImpulsFile, ImpulsProtocol
from .utils import ImpulsExcelProcessor, ImpulsProtocolGenerator

# Получаем логгеры
logger = logging.getLogger('impuls_analysis')
excel_logger = logging.getLogger('celery.module.impuls_analysis.excel_processing')
protocol_logger = logging.getLogger('celery.module.impuls_analysis.protocol_generation')
analysis_logger = logging.getLogger('celery.module.impuls_analysis.data_analysis')


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.process_excel_files')
def process_excel_files(self, analysis_id: str):
    """
    Задача для обработки загруженных Excel файлов
    
    Args:
        analysis_id: ID анализа импульса
    """
    try:
        analysis = ImpulsAnalysis.objects.get(id=analysis_id)
        analysis.status = 'processing'
        analysis.task_id = self.request.id
        analysis.save()
        
        excel_logger.info(f"Начало обработки Excel файлов для анализа {analysis_id}")
        
        # Получаем загруженные файлы
        files = analysis.files.all()
        if not files.exists():
            raise ValueError("Нет загруженных файлов для обработки")
        
        # Обрабатываем каждый файл
        processor = ImpulsExcelProcessor()
        processed_data = {}
        
        for file_obj in files:
            excel_logger.info(f"Обработка файла: {file_obj.original_filename}")
            
            # Обрабатываем Excel файл (заглушка - будет реализована позже)
            file_data = processor.process_file(file_obj.file.path, file_obj.file_type)
            processed_data[file_obj.file_type] = file_data
            
            excel_logger.info(f"Файл {file_obj.original_filename} успешно обработан")
        
        # Сохраняем результаты обработки
        analysis.analysis_results = {
            'processed_files': len(files),
            'file_types': list(processed_data.keys()),
            'processing_completed_at': timezone.now().isoformat(),
            'processed_data': processed_data
        }
        analysis.status = 'completed'
        analysis.save()
        
        excel_logger.info(f"Обработка Excel файлов для анализа {analysis_id} завершена успешно")
        
        # Запускаем задачу генерации протокола
        generate_protocol.delay(analysis_id)
        
    except Exception as e:
        error_msg = f"Ошибка при обработке Excel файлов: {str(e)}"
        excel_logger.error(error_msg, exc_info=True)
        
        try:
            analysis = ImpulsAnalysis.objects.get(id=analysis_id)
            analysis.status = 'failed'
            analysis.error_message = error_msg
            analysis.save()
        except:
            pass
        
        raise


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.analyze_impuls_data')
def analyze_impuls_data(self, analysis_id: str):
    """
    Задача для анализа данных импульса
    
    Args:
        analysis_id: ID анализа импульса
    """
    try:
        analysis = ImpulsAnalysis.objects.get(id=analysis_id)
        analysis_logger.info(f"Начало анализа данных импульса для анализа {analysis_id}")
        
        # Получаем обработанные данные
        processed_data = (analysis.analysis_results or {}).get('processed_data', {})
        if not processed_data:
            raise ValueError("Нет обработанных данных для анализа")
        
        # Анализируем данные (заглушка - будет реализована позже)
        analysis_results = {
            'analysis_type': analysis.analysis_type,
            'analysis_completed_at': timezone.now().isoformat(),
            'results': {
                'force_calculation': processed_data.get('force_calculation', {}),
                'experiment_plan': processed_data.get('experiment_plan', {}),
            }
        }
        
        # Обновляем результаты анализа
        merged = (analysis.analysis_results or {}).copy()
        merged.update(analysis_results)
        analysis.analysis_results = merged
        analysis.save()
        
        analysis_logger.info(f"Анализ данных импульса для анализа {analysis_id} завершен успешно")
        
    except Exception as e:
        error_msg = f"Ошибка при анализе данных импульса: {str(e)}"
        analysis_logger.error(error_msg, exc_info=True)
        raise


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.generate_protocol')
def generate_protocol(self, analysis_id: str):
    """
    Задача для генерации протокола анализа
    
    Args:
        analysis_id: ID анализа импульса
    """
    try:
        analysis = ImpulsAnalysis.objects.get(id=analysis_id)
        protocol_logger.info(f"Начало генерации протокола для анализа {analysis_id}")
        
        # Проверяем, что анализ завершен
        if analysis.status != 'completed':
            raise ValueError(f"Анализ должен быть завершен, текущий статус: {analysis.status}")
        
        # Генерируем протокол (заглушка - будет реализована позже)
        generator = ImpulsProtocolGenerator()
        protocol_content = generator.generate_protocol(analysis)
        
        # Создаем файл протокола
        filename = f"protocol_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        protocol_file = ContentFile(protocol_content, name=filename)
        
        # Сохраняем протокол
        protocol = ImpulsProtocol.objects.create(
            analysis=analysis,
            protocol_file=protocol_file
        )
        
        protocol_logger.info(f"Протокол для анализа {analysis_id} успешно сгенерирован: {protocol.id}")
        
    except Exception as e:
        error_msg = f"Ошибка при генерации протокола: {str(e)}"
        protocol_logger.error(error_msg, exc_info=True)
        raise


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.bulk_download_protocols')
def bulk_download_protocols(self, analysis_ids: list, user_id: str):
    """
    Задача для массового скачивания протоколов в виде архива
    
    Args:
        analysis_ids: Список ID анализов
        user_id: ID пользователя
    """
    try:
        protocol_logger.info(f"Начало создания архива протоколов для {len(analysis_ids)} анализов")
        
        # Создаем архив в памяти
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            for analysis_id in analysis_ids:
                try:
                    analysis = ImpulsAnalysis.objects.get(id=analysis_id)
                    protocols = analysis.protocols.all()
                    
                    for protocol in protocols:
                        if protocol.protocol_file:
                            # Читаем файл протокола
                            with open(protocol.protocol_file.path, 'rb') as f:
                                protocol_content = f.read()
                            
                            # Добавляем в архив
                            archive_name = f"{analysis.title}_{protocol.generated_at.strftime('%Y%m%d_%H%M')}.docx"
                            zip_file.writestr(archive_name, protocol_content)
                            
                except Exception as e:
                    protocol_logger.warning(f"Ошибка при обработке анализа {analysis_id}: {str(e)}")
                    continue
        
        # Сохраняем архив в media
        archive_filename = f"protocols_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        archive_path = os.path.join('impuls_analysis', 'archives', archive_filename)
        
        # Создаем директорию если не существует
        archive_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'archives')
        os.makedirs(archive_dir, exist_ok=True)
        
        # Сохраняем файл
        archive_full_path = os.path.join(settings.MEDIA_ROOT, archive_path)
        with open(archive_full_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        protocol_logger.info(f"Архив протоколов успешно создан: {archive_path}")
        
        return {
            'archive_path': archive_path,
            'archive_filename': archive_filename,
            'analyses_count': len(analysis_ids),
            'created_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Ошибка при создании архива протоколов: {str(e)}"
        protocol_logger.error(error_msg, exc_info=True)
        raise


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.cleanup_old_files')
def cleanup_old_files(self, days_old: int = 30):
    """
    Задача для очистки старых файлов
    
    Args:
        days_old: Количество дней для определения старых файлов
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        # Удаляем старые протоколы
        old_protocols = ImpulsProtocol.objects.filter(generated_at__lt=cutoff_date)
        deleted_protocols = old_protocols.count()
        
        for protocol in old_protocols:
            if protocol.protocol_file:
                try:
                    os.remove(protocol.protocol_file.path)
                except OSError:
                    pass
            protocol.delete()
        
        # Удаляем старые файлы Excel
        old_files = ImpulsFile.objects.filter(uploaded_at__lt=cutoff_date)
        deleted_files = old_files.count()
        
        for file_obj in old_files:
            if file_obj.file:
                try:
                    os.remove(file_obj.file.path)
                except OSError:
                    pass
            file_obj.delete()
        
        logger.info(f"Очистка завершена: удалено {deleted_protocols} протоколов и {deleted_files} файлов")
        
        return {
            'deleted_protocols': deleted_protocols,
            'deleted_files': deleted_files,
            'cleanup_date': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Ошибка при очистке старых файлов: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise
