from celery import shared_task
from django.utils import timezone
from src.modules.education_materials_parser.fgos.scripts import FgosParser
from src.modules.education_materials_parser.fgos.models import FgosParsingSession


@shared_task(bind=True, name='fgos.parse_all_documents')
def parse_all_fgos_documents(self):
    """
    Celery задача для полного парсинга всех документов ФГОС
    """
    try:
        print("Запуск полного парсинга ФГОС...")
        
        # Создаем парсер и запускаем полный парсинг
        parser = FgosParser()
        session = parser.run_full_parsing()
        
        return {
            'status': 'success',
            'session_id': str(session.id),
            'total_documents_found': session.total_documents_found,
            'new_documents_added': session.new_documents_added,
            'documents_updated': session.documents_updated,
            'files_downloaded': session.files_downloaded,
            'download_errors': session.download_errors,
            'started_at': session.started_at.isoformat(),
            'finished_at': session.finished_at.isoformat() if session.finished_at else None,
        }
        
    except Exception as e:
        print(f"Ошибка в задаче парсинга ФГОС: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='fgos.download_missing_files')
def download_missing_fgos_files(self):
    """
    Celery задача для скачивания недостающих PDF файлов
    """
    try:
        from src.modules.education_materials_parser.fgos.models import FgosDocument
        
        print("Поиск документов без скачанных файлов...")
        
        # Находим документы без скачанных файлов
        missing_files = FgosDocument.objects.filter(is_downloaded=False)
        
        if not missing_files.exists():
            print("Все файлы уже скачаны")
            return {
                'status': 'success',
                'message': 'Все файлы уже скачаны',
                'downloaded': 0,
                'errors': 0
            }
        
        print(f"Найдено {missing_files.count()} документов без файлов")
        
        # Создаем парсер
        parser = FgosParser()
        
        downloaded = 0
        errors = 0
        
        for doc in missing_files:
            try:
                print(f"Скачивание файла для документа: {doc.title}")
                
                file_path = parser.media_path + f"/{doc.uuid}.pdf"
                success, result = parser.download_pdf(doc.download_url, file_path)
                
                if success:
                    doc.is_downloaded = True
                    doc.file_size = result
                    doc.download_error = None
                    downloaded += 1
                    print(f"✓ Файл скачан: {doc.title}")
                else:
                    doc.is_downloaded = False
                    doc.download_error = str(result)
                    errors += 1
                    print(f"✗ Ошибка скачивания: {doc.title}")
                
                doc.save()
                
                # Небольшая задержка между скачиваниями
                import time
                time.sleep(1)
                
            except Exception as e:
                print(f"Ошибка при скачивании файла для документа {doc.id}: {e}")
                doc.download_error = str(e)
                doc.save()
                errors += 1
        
        return {
            'status': 'success',
            'downloaded': downloaded,
            'errors': errors,
            'total_processed': downloaded + errors
        }
        
    except Exception as e:
        print(f"Ошибка в задаче скачивания файлов ФГОС: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='fgos.update_existing_documents')
def update_existing_fgos_documents(self):
    """
    Celery задача для обновления существующих документов ФГОС
    """
    try:
        from src.modules.education_materials_parser.fgos.models import FgosDocument
        
        print("Обновление существующих документов ФГОС...")
        
        # Создаем парсер
        parser = FgosParser()
        
        # Получаем все существующие документы
        existing_docs = FgosDocument.objects.all()
        
        if not existing_docs.exists():
            print("Нет существующих документов для обновления")
            return {
                'status': 'success',
                'message': 'Нет документов для обновления',
                'updated': 0,
                'errors': 0
            }
        
        updated = 0
        errors = 0
        
        for doc in existing_docs:
            try:
                print(f"Обновление документа: {doc.title}")
                
                # Парсим страницу заново
                document_data = parser.parse_fgos_page(doc.source_url)
                
                if document_data:
                    # Обновляем данные документа
                    for key, value in document_data.items():
                        if value is not None and hasattr(doc, key):
                            setattr(doc, key, value)
                    
                    doc.updated_at = timezone.now()
                    doc.save()
                    updated += 1
                    print(f"✓ Документ обновлен: {doc.title}")
                else:
                    print(f"✗ Не удалось получить данные для документа: {doc.title}")
                    errors += 1
                
                # Небольшая задержка между запросами
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"Ошибка при обновлении документа {doc.id}: {e}")
                errors += 1
        
        return {
            'status': 'success',
            'updated': updated,
            'errors': errors,
            'total_processed': updated + errors
        }
        
    except Exception as e:
        print(f"Ошибка в задаче обновления документов ФГОС: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='fgos.cleanup_orphaned_files')
def cleanup_orphaned_fgos_files(self):
    """
    Celery задача для очистки файлов без соответствующих записей в БД
    """
    try:
        import os
        from src.modules.education_materials_parser.fgos.models import FgosDocument
        from django.conf import settings
        
        print("Поиск файлов-сирот...")
        
        media_path = os.path.join(settings.MEDIA_ROOT, 'education_materials_parser')
        
        if not os.path.exists(media_path):
            return {
                'status': 'success',
                'message': 'Папка media не существует',
                'deleted': 0
            }
        
        # Получаем все UUID из БД
        existing_uuids = set(FgosDocument.objects.values_list('uuid', flat=True))
        
        # Получаем все PDF файлы в папке
        pdf_files = [f for f in os.listdir(media_path) if f.endswith('.pdf')]
        
        deleted = 0
        
        for pdf_file in pdf_files:
            try:
                # Извлекаем UUID из имени файла
                uuid_str = pdf_file.replace('.pdf', '')
                
                # Проверяем, есть ли соответствующая запись в БД
                if uuid_str not in [str(uuid) for uuid in existing_uuids]:
                    file_path = os.path.join(media_path, pdf_file)
                    os.remove(file_path)
                    deleted += 1
                    print(f"Удален файл-сирота: {pdf_file}")
                    
            except Exception as e:
                print(f"Ошибка при удалении файла {pdf_file}: {e}")
        
        return {
            'status': 'success',
            'deleted': deleted,
            'total_files_checked': len(pdf_files)
        }
        
    except Exception as e:
        print(f"Ошибка в задаче очистки файлов ФГОС: {e}")
        return {
            'status': 'error',
            'error': str(e)
        } 