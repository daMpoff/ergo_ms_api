from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from src.modules.education_materials_parser.fgos.scripts import FgosParser
from src.modules.education_materials_parser.fgos.models import FgosDocument, FgosParsingSession


class Command(BaseCommand):
    help = 'Парсинг документов ФГОС с сайта fgos.ru'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Полный парсинг всех документов ФГОС',
        )
        parser.add_argument(
            '--download-missing',
            action='store_true',
            help='Скачать недостающие PDF файлы',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Обновить существующие документы',
        )
        parser.add_argument(
            '--cleanup-files',
            action='store_true',
            help='Очистить файлы-сироты',
        )
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='Показать статистику',
        )
        parser.add_argument(
            '--url',
            type=str,
            help='Парсить конкретную страницу ФГОС по URL',
        )

    def handle(self, *args, **options):
        if options['show_stats']:
            self.show_statistics()
            return

        if options['full']:
            self.run_full_parsing()
        elif options['download_missing']:
            self.download_missing_files()
        elif options['update_existing']:
            self.update_existing_documents()
        elif options['cleanup_files']:
            self.cleanup_orphaned_files()
        elif options['url']:
            self.parse_single_url(options['url'])
        else:
            self.stdout.write(
                self.style.ERROR('Укажите одну из опций: --full, --download-missing, --update-existing, --cleanup-files, --show-stats, или --url')
            )

    def show_statistics(self):
        """Показать статистику парсинга"""
        self.stdout.write(self.style.SUCCESS('\n=== Статистика ФГОС ==='))
        
        # Общая статистика документов
        total_docs = FgosDocument.objects.count()
        downloaded_docs = FgosDocument.objects.filter(is_downloaded=True).count()
        failed_downloads = FgosDocument.objects.filter(is_downloaded=False).count()
        
        self.stdout.write(f'Всего документов: {total_docs}')
        self.stdout.write(f'Скачанных файлов: {downloaded_docs}')
        self.stdout.write(f'Не скачанных файлов: {failed_downloads}')
        
        # Статистика по уровням образования
        levels = FgosDocument.objects.values_list('level', flat=True).distinct()
        self.stdout.write('\n--- По уровням образования ---')
        for level in levels:
            if level:
                count = FgosDocument.objects.filter(level=level).count()
                self.stdout.write(f'{level}: {count}')
        
        # Последние сессии парсинга
        recent_sessions = FgosParsingSession.objects.order_by('-started_at')[:5]
        if recent_sessions:
            self.stdout.write('\n--- Последние сессии парсинга ---')
            for session in recent_sessions:
                status_color = self.style.SUCCESS if session.status == 'completed' else self.style.ERROR
                self.stdout.write(
                    f'{session.started_at.strftime("%Y-%m-%d %H:%M")} - '
                    f'{status_color(session.status)} - '
                    f'Документов: {session.total_documents_found}, '
                    f'Скачано: {session.files_downloaded}'
                )

    def run_full_parsing(self):
        """Запустить полный парсинг"""
        self.stdout.write(self.style.SUCCESS('Запуск полного парсинга ФГОС...'))
        
        try:
            parser = FgosParser()
            session = parser.run_full_parsing()
            
            self.stdout.write(self.style.SUCCESS(f'\nПарсинг завершен!'))
            self.stdout.write(f'ID сессии: {session.id}')
            self.stdout.write(f'Статус: {session.status}')
            self.stdout.write(f'Найдено документов: {session.total_documents_found}')
            self.stdout.write(f'Новых документов: {session.new_documents_added}')
            self.stdout.write(f'Обновлено документов: {session.documents_updated}')
            self.stdout.write(f'Скачано файлов: {session.files_downloaded}')
            self.stdout.write(f'Ошибок скачивания: {session.download_errors}')
            
            if session.error_message:
                self.stdout.write(self.style.ERROR(f'Ошибка: {session.error_message}'))
                
        except Exception as e:
            raise CommandError(f'Ошибка при парсинге: {e}')

    def download_missing_files(self):
        """Скачать недостающие файлы"""
        self.stdout.write(self.style.SUCCESS('Скачивание недостающих файлов...'))
        
        missing_files = FgosDocument.objects.filter(is_downloaded=False)
        
        if not missing_files.exists():
            self.stdout.write(self.style.SUCCESS('Все файлы уже скачаны!'))
            return
        
        self.stdout.write(f'Найдено {missing_files.count()} документов без файлов')
        
        try:
            parser = FgosParser()
            
            downloaded = 0
            errors = 0
            
            for doc in missing_files:
                self.stdout.write(f'Скачивание: {doc.title}')
                
                file_path = parser.media_path + f"/{doc.uuid}.pdf"
                success, result = parser.download_pdf(doc.download_url, file_path)
                
                if success:
                    doc.is_downloaded = True
                    doc.file_size = result
                    doc.download_error = None
                    downloaded += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Скачан'))
                else:
                    doc.is_downloaded = False
                    doc.download_error = str(result)
                    errors += 1
                    self.stdout.write(self.style.ERROR(f'✗ Ошибка: {result}'))
                
                doc.save()
            
            self.stdout.write(self.style.SUCCESS(f'\nГотово! Скачано: {downloaded}, Ошибок: {errors}'))
            
        except Exception as e:
            raise CommandError(f'Ошибка при скачивании файлов: {e}')

    def update_existing_documents(self):
        """Обновить существующие документы"""
        self.stdout.write(self.style.SUCCESS('Обновление существующих документов...'))
        
        existing_docs = FgosDocument.objects.all()
        
        if not existing_docs.exists():
            self.stdout.write(self.style.WARNING('Нет документов для обновления'))
            return
        
        try:
            parser = FgosParser()
            
            updated = 0
            errors = 0
            
            for doc in existing_docs:
                self.stdout.write(f'Обновление: {doc.title}')
                
                document_data = parser.parse_fgos_page(doc.source_url)
                
                if document_data:
                    for key, value in document_data.items():
                        if value is not None and hasattr(doc, key):
                            setattr(doc, key, value)
                    
                    doc.updated_at = timezone.now()
                    doc.save()
                    updated += 1
                    self.stdout.write(self.style.SUCCESS('✓ Обновлен'))
                else:
                    errors += 1
                    self.stdout.write(self.style.ERROR('✗ Ошибка при получении данных'))
            
            self.stdout.write(self.style.SUCCESS(f'\nГотово! Обновлено: {updated}, Ошибок: {errors}'))
            
        except Exception as e:
            raise CommandError(f'Ошибка при обновлении документов: {e}')

    def cleanup_orphaned_files(self):
        """Очистить файлы-сироты"""
        self.stdout.write(self.style.SUCCESS('Поиск файлов-сирот...'))
        
        try:
            import os
            from django.conf import settings
            
            media_path = os.path.join(settings.MEDIA_ROOT, 'education_materials_parser')
            
            if not os.path.exists(media_path):
                self.stdout.write(self.style.WARNING('Папка media не существует'))
                return
            
            # Получаем все UUID из БД
            existing_uuids = set(str(uuid) for uuid in FgosDocument.objects.values_list('uuid', flat=True))
            
            # Получаем все PDF файлы в папке
            pdf_files = [f for f in os.listdir(media_path) if f.endswith('.pdf')]
            
            deleted = 0
            
            for pdf_file in pdf_files:
                uuid_str = pdf_file.replace('.pdf', '')
                
                if uuid_str not in existing_uuids:
                    file_path = os.path.join(media_path, pdf_file)
                    os.remove(file_path)
                    deleted += 1
                    self.stdout.write(f'Удален файл-сирота: {pdf_file}')
            
            if deleted == 0:
                self.stdout.write(self.style.SUCCESS('Файлы-сироты не найдены'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Удалено {deleted} файлов-сирот'))
                
        except Exception as e:
            raise CommandError(f'Ошибка при очистке файлов: {e}')

    def parse_single_url(self, url):
        """Парсить конкретную страницу"""
        self.stdout.write(self.style.SUCCESS(f'Парсинг страницы: {url}'))
        
        try:
            parser = FgosParser()
            
            # Парсим страницу
            document_data = parser.parse_fgos_page(url)
            
            if not document_data:
                raise CommandError('Не удалось извлечь данные со страницы')
            
            # Сохраняем в БД
            doc, is_new = parser.save_or_update_document(document_data)
            
            if not doc:
                raise CommandError('Не удалось сохранить документ')
            
            status = 'создан' if is_new else 'обновлен'
            self.stdout.write(self.style.SUCCESS(f'Документ {status}: {doc.title}'))
            
            # Пытаемся скачать файл
            file_path = parser.media_path + f"/{doc.uuid}.pdf"
            success, result = parser.download_pdf(document_data['download_url'], file_path)
            
            if success:
                doc.is_downloaded = True
                doc.file_size = result
                doc.download_error = None
                self.stdout.write(self.style.SUCCESS(f'✓ Файл скачан ({result} байт)'))
            else:
                doc.is_downloaded = False
                doc.download_error = str(result)
                self.stdout.write(self.style.ERROR(f'✗ Ошибка скачивания: {result}'))
            
            doc.save()
            
        except Exception as e:
            raise CommandError(f'Ошибка при парсинге страницы: {e}') 