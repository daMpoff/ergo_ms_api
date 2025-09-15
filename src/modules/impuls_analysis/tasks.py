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
from src.modules.impuls_analysis.models import (
    ImpulsForceRecord,
    ImpulsPlanRecord,
    ImpulsAnalysis,
    ImpulsExtremum,
    ImpulsProtocol,
    ImpulsFile,
)
from src.modules.impuls_analysis.utils import ImpulsExcelProcessor, run_protocol_analysis
from src.modules.impuls_analysis.word_processor import generate_protocol_document

# Получаем логгеры
logger = logging.getLogger('impuls_analysis')
excel_logger = logging.getLogger('celery.module.impuls_analysis.excel_processing')
protocol_logger = logging.getLogger('celery.module.impuls_analysis.protocol_generation')
analysis_logger = logging.getLogger('celery.module.impuls_analysis.data_analysis')


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.import_impuls_excel')
def import_impuls_excel(self, file_path: str, file_type: str):
    """
    Импортирует один Excel-файл в соответствующую таблицу без привязки к анализам.
    file_type: 'force' | 'plan'
    """
    try:
        excel_logger.info(f"Импорт файла: {file_path} (type={file_type})")
        processor = ImpulsExcelProcessor()

        if file_type == 'force':
            recs = processor.parse_force_records(file_path)
            # Оставляем только новые протоколы
            incoming_protocols = {str(r.get('protocol_number') or '') for r in recs}
            existing_protocols = set(
                ImpulsForceRecord.objects.filter(protocol_number__in=incoming_protocols)
                .values_list('protocol_number', flat=True)
            )
            filtered = [r for r in recs if str(r.get('protocol_number') or '') not in existing_protocols]
            bulk = [
                ImpulsForceRecord(
                    sheet_title=r.get('sheet_title') or '',
                    protocol_number=str(r.get('protocol_number') or ''),
                    pct_static=r.get('pct_static'),
                    v=r.get('v'), p=r.get('p'), f=r.get('f'),
                    energy_j=r.get('energy_j'), velocity_ms=r.get('velocity_ms'), force_n=r.get('force_n'),
                ) for r in filtered
            ]
            created = 0
            if bulk:
                ImpulsForceRecord.objects.bulk_create(bulk, batch_size=1000)
                created = len(bulk)
            excel_logger.info(
                f"Импорт force завершен. Протоколов входящих: {len(incoming_protocols)}, уже существующих: {len(existing_protocols)}, добавлено записей: {created}"
            )
            return {'type': 'force', 'protocols_incoming': len(incoming_protocols), 'protocols_existing': len(existing_protocols), 'records_created': created}

        elif file_type == 'plan':
            recs = processor.parse_plan_records(file_path)
            incoming_protocols = {str(r.get('protocol_number') or '') for r in recs}
            existing_protocols = set(
                ImpulsPlanRecord.objects.filter(protocol_number__in=incoming_protocols)
                .values_list('protocol_number', flat=True)
            )
            filtered = [r for r in recs if str(r.get('protocol_number') or '') not in existing_protocols]
            bulk = []
            for r in filtered:
                bulk.append(ImpulsPlanRecord(
                    protocol_number=str(r.get('protocol_number') or ''),
                    p_static=r.get('p_static'),
                    p_static_value=r.get('p_static_value'),
                    l1_l2_ratio=(int(r.get('L1/L2')) if r.get('L1/L2') is not None else None),
                    l1_m=r.get('L1 (м)'), d1_m=r.get('d1 (м)'), m1_kg=r.get('m1 (кг)'),
                    l2_m=r.get('L2 (м)'), d2_m=r.get('d2 (м)'),
                    t_s=r.get('Т (с)'), a_j=r.get('А, (Дж)'), v_ms=r.get('V, (м/с)'),
                    c12_kg_s=r.get('С1,2 (кг/с)'), p_n=r.get('Р, (Н)'),
                ))
            created = 0
            if bulk:
                ImpulsPlanRecord.objects.bulk_create(bulk, batch_size=1000)
                created = len(bulk)
            excel_logger.info(
                f"Импорт plan завершен. Протоколов входящих: {len(incoming_protocols)}, уже существующих: {len(existing_protocols)}, добавлено записей: {created}"
            )
            return {'type': 'plan', 'protocols_incoming': len(incoming_protocols), 'protocols_existing': len(existing_protocols), 'records_created': created}

        else:
            raise ValueError(f"Неизвестный тип файла: {file_type}")

    except Exception as e:
        error_msg = f"Ошибка при импорте файла: {str(e)}"
        excel_logger.error(error_msg, exc_info=True)
        raise


@shared_task(bind=True, name='src.modules.impuls_analysis.tasks.create_analysis_by_protocol')
def create_analysis_by_protocol(self, protocol_number: str, user_id: int, title: str = None, description: str = None, analysis_id: str = None):
    """
    Создает ImpulsAnalysis по номеру протокола:
    - проверяет наличие данных в обеих таблицах
    - строит 2 графика и сохраняет в media/impuls_analysis/analyses с UUID-именами
    - сохраняет экстремумы в отдельную таблицу ImpulsExtremum
    """
    try:
        analysis_logger.info(f"Запуск анализа протокола {protocol_number} (user_id={user_id})")

        # Проверка наличия данных
        if not ImpulsForceRecord.objects.filter(protocol_number=protocol_number).exists() or \
           not ImpulsPlanRecord.objects.filter(protocol_number=protocol_number).exists():
            raise ValueError("Для указанного протокола должны существовать записи в ImpulsForceRecord и ImpulsPlanRecord.")

        # Создание/обновление записи анализа
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(id=user_id).first()
        if user is None:
            raise ValueError(f"Пользователь не найден (id={user_id})")

        # Если передан analysis_id, обновляем существующую запись вместо создания новой
        if analysis_id:
            analysis = ImpulsAnalysis.objects.filter(id=analysis_id, user=user).first()
            if analysis is None:
                # Если по каким-то причинам запись не найдена, создаем новую
                analysis = ImpulsAnalysis.objects.create(
                    user=user,
                    title=title or f"Протокол {protocol_number}",
                    description=description or f"Анализ по протоколу {protocol_number}",
                    status='processing',
                    protocol_number=protocol_number,
                )
            else:
                # Обнуляем связанные артефакты и переводим в processing
                try:
                    files_deleted = analysis.delete_analysis_files()
                    analysis_logger.info(f"Удалено файлов: {files_deleted}")
                except Exception:
                    pass
                analysis.status = 'processing'
                analysis.error_message = ''
                analysis.started_at = None
                analysis.completed_at = None
                analysis.protocol_number = protocol_number
                if title:
                    analysis.title = title
                if description:
                    analysis.description = description
                analysis.save()
        else:
            # Режим обратной совместимости: создаем новый анализ
            analysis = ImpulsAnalysis.objects.create(
                user=user,
                title=title or f"Протокол {protocol_number}",
                description=description or f"Анализ по протоколу {protocol_number}",
                status='processing',
                protocol_number=protocol_number,
            )

        # Запуск утилиты анализа с ID анализа
        results = run_protocol_analysis(protocol_number, str(analysis.id))

        # Обновляем базовые поля анализа (без завершения)
        analysis.protocol_number = results['protocol_number']
        analysis.p_static = results['p_static']
        analysis.energy_j = results['energy_j']
        analysis.save()

        # Сохраняем экстремумы в отдельную таблицу
        extremum_objects = []
        for pulse_data in results['pulse_maxima']:
            extremum_objects.append(ImpulsExtremum(
                analysis=analysis,
                pulse_id=pulse_data['pulse_id'],
                extremum_id=pulse_data['extremum_id'],
                extremum_type=pulse_data['extremum_type'] or 'max',
                v=pulse_data['v'],
                f=pulse_data['f'],
                duration_v=pulse_data['duration_v'],
                area=pulse_data['area'],
                v_start=pulse_data['v_start'],
                v_end=pulse_data['v_end'],
            ))
        
        if extremum_objects:
            ImpulsExtremum.objects.bulk_create(extremum_objects, batch_size=100)

        # Генерируем Word протокол (может занять время). Завершаем только после успеха
        protocol_path = generate_protocol_document(protocol_number, str(analysis.id))

        # Помечаем анализ завершенным только после успешной генерации протокола
        analysis.status = 'completed'
        analysis.completed_at = timezone.now()
        analysis.save()
        
        analysis_logger.info(f"Анализ обновлен {analysis.id} для протокола {protocol_number}, экстремумов: {len(extremum_objects)}")
        return {
            'analysis_id': str(analysis.id), 
            'protocol_number': protocol_number, 
            'extrema_count': len(extremum_objects),
            'protocol_path': protocol_path,
        }

    except Exception as e:
        error_msg = f"Ошибка при создании анализа по протоколу {protocol_number}: {str(e)}"
        analysis_logger.error(error_msg, exc_info=True)
        # Обновляем статус анализа на ошибку
        try:
            if 'analysis' in locals():
                analysis.status = 'failed'
                analysis.error_message = str(e)
                analysis.completed_at = timezone.now()
                analysis.save()
        except Exception:
            pass
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
