"""
Django команда для быстрой установки основных TTS моделей
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Быстрая установка основных TTS моделей для video_analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--languages',
            nargs='+',
            default=['ru'],
            choices=['ru', 'en', 'fr', 'de', 'es'],
            help='Языки для установки (по умолчанию: ru)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно переустановить модели'
        )

    def handle(self, *args, **options):
        languages = options['languages']
        force = options['force']
        
        # Убедимся, что локальный репозиторий Silero установлен
        try:
            call_command('install_silero_repo')
        except Exception as e:
            raise CommandError(f'Не удалось подготовить локальный репозиторий Silero: {e}')
        
        # Модели по умолчанию для каждого языка
        default_models = {
            'ru': ['v3_1_ru', 'baya', 'kseniya'],
            'en': ['v3_en'],
            'fr': ['v3_fr'],
            'de': ['v3_de'],
            'es': ['v3_es']
        }
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Установка TTS моделей для video_analysis')
        )
        self.stdout.write(f'Языки: {", ".join(languages)}')
        self.stdout.write('')
        
        total_installed = 0
        total_errors = 0
        
        for language in languages:
            speakers = default_models.get(language, ['v3_1_ru'])
            
            self.stdout.write(f'📦 Установка моделей для языка: {language}')
            
            for speaker in speakers:
                try:
                    self.stdout.write(f'   Установка {language}_{speaker}...')
                    
                    call_command(
                        'install_tts_model',
                        language=language,
                        speaker=speaker,
                        force=force,
                        verbosity=0  # Подавляем вывод подкоманды
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✅ {language}_{speaker} установлена')
                    )
                    total_installed += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'   ❌ Ошибка установки {language}_{speaker}: {e}')
                    )
                    total_errors += 1
            
            self.stdout.write('')
        
        # Показываем итоги
        self.stdout.write('📊 Итоги установки:')
        self.stdout.write(f'   Успешно установлено: {total_installed}')
        if total_errors > 0:
            self.stdout.write(f'   Ошибок: {total_errors}')
        
        # Показываем установленные модели
        self.stdout.write('')
        self.stdout.write('📋 Проверка установленных моделей:')
        try:
            call_command('manage_tts_models', 'list', verbosity=1)
        except:
            pass
        
        if total_installed > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('🎉 Установка завершена! TTS модели готовы к использованию.')
            )
            self.stdout.write('')
            self.stdout.write('Для тестирования модели выполните:')
            self.stdout.write('python manage.py manage_tts_models test --language ru --speaker v3_1_ru')
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('⚠️ Ни одна модель не была установлена.')
            )
