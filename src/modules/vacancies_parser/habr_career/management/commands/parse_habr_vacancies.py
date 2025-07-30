import json
import os
import sys
from django.core.management.base import BaseCommand

from src.modules.vacancies_parser.habr_career.scripts import parse_habr_vacancies, parse_habr_archived_vacancies, parse_habr_all_vacancies
from src.modules.vacancies_parser.habr_career.tasks import parse_habr_vacancies_task, parse_habr_archived_vacancies_task, parse_habr_all_vacancies_task

from celery.result import AsyncResult


class Command(BaseCommand):
    help = 'Парсинг вакансий с Хабр Карьеры'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            default='config.json',
            help='Путь к JSON конфигурационному файлу (по умолчанию config.json)'
        )
        parser.add_argument(
            '--access-token',
            type=str,
            help='Access token для API Хабр Карьеры (переопределяет config)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            help='Количество страниц для парсинга (переопределяет config)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            help='Задержка между запросами в секундах (переопределяет config)'
        )
        parser.add_argument(
            '--no-details',
            action='store_true',
            help='Не получать детальную информацию о вакансиях (быстрее)'
        )
        parser.add_argument(
            '--archived',
            action='store_true',
            help='Парсить только архивные вакансии'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Парсить все вакансии (активные и архивные)'
        )
        parser.add_argument(
            '--use-config-only',
            action='store_true',
            help='Использовать только настройки из конфигурационного файла'
        )
        parser.add_argument(
            '--wait',
            action='store_true',
            help='Дождаться завершения задачи Celery и вывести результат'
        )
        parser.add_argument(
            '--celery',
            action='store_true',
            help='Запустить парсинг через Celery'
        )
    
    def load_config(self, config_path):
        """Загрузка конфигурации из JSON файла"""
        try:
            # Получаем абсолютный путь к конфигурационному файлу
            if not os.path.isabs(config_path):
                # Путь относительно папки с командой
                current_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(current_dir, config_path)
            
            if not os.path.exists(config_path):
                self.stdout.write(
                    self.style.WARNING(f'Конфигурационный файл {config_path} не найден. Используем значения по умолчанию.')
                )
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.stdout.write(
                self.style.SUCCESS(f'Конфигурация загружена из {config_path}')
            )
            return config
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при загрузке конфигурации: {e}')
            )
            return {}
    
    def print_formatted_result(self, result):
        """Вывод результата в удобном формате"""
        if isinstance(result, dict):
            if 'status' in result:
                if result['status'] == 'SUCCESS':
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ {result.get('message', 'Задача выполнена успешно')}")
                    )
                    if 'result' in result:
                        stats = result['result']
                        if isinstance(stats, dict):
                            self.stdout.write(f"📊 Статистика:")
                            self.stdout.write(f"   Всего обработано: {stats.get('total', 0)}")
                            self.stdout.write(f"   Новых вакансий: {stats.get('new', 0)}")
                            self.stdout.write(f"   Обновлено вакансий: {stats.get('updated', 0)}")
                            self.stdout.write(f"   Ошибок: {stats.get('errors', 0)}")
                elif result['status'] == 'ERROR':
                    self.stdout.write(
                        self.style.ERROR(f"❌ {result.get('message', 'Произошла ошибка')}")
                    )
                    if 'error' in result:
                        self.stdout.write(f"🔍 Детали ошибки: {result['error']}")
                else:
                    self.stdout.write(f"ℹ️ {result}")
            else:
                self.stdout.write(f"📋 Результат: {result}")
        else:
            self.stdout.write(f"📋 Результат: {result}")
    
    def handle(self, *args, **options):
        # Загружаем конфигурацию
        config = self.load_config(options['config'])
        
        # Определяем параметры
        access_token = options.get('access_token') or config.get('access_token')
        pages = options.get('pages') or config.get('pages', 5)
        delay = options.get('delay') or config.get('delay', 1.0)
        get_details = not options.get('no_details', False) and config.get('get_details', True)
        parse_archived = options.get('archived', False) or config.get('parse_archived', False)
        parse_all = options.get('all', False) or config.get('parse_all', False)
        use_celery = options.get('celery', False)
        wait_for_result = options.get('wait', False)
        
        # Проверяем обязательные параметры
        if not access_token:
            self.stdout.write(
                self.style.ERROR('❌ Ошибка: Не указан access_token для API Хабр Карьеры')
            )
            self.stdout.write(
                self.style.WARNING('💡 Укажите токен в конфигурационном файле или передайте через --access-token')
            )
            return
        
        # Выводим параметры
        self.stdout.write(f"🔧 Параметры парсинга:")
        self.stdout.write(f"   Access Token: {'*' * 10}{access_token[-4:] if access_token else 'Не указан'}")
        self.stdout.write(f"   Страниц: {pages}")
        self.stdout.write(f"   Задержка: {delay}с")
        self.stdout.write(f"   Детали: {'Да' if get_details else 'Нет'}")
        self.stdout.write(f"   Архивные: {'Да' if parse_archived else 'Нет'}")
        self.stdout.write(f"   Все вакансии: {'Да' if parse_all else 'Нет'}")
        self.stdout.write(f"   Celery: {'Да' if use_celery else 'Нет'}")
        
        try:
            if use_celery:
                # Запускаем через Celery
                if parse_all:
                    task = parse_habr_all_vacancies_task.delay(
                        access_token=access_token,
                        pages=pages,
                        delay=delay,
                        get_details=get_details
                    )
                elif parse_archived:
                    task = parse_habr_archived_vacancies_task.delay(
                        access_token=access_token,
                        pages=pages,
                        delay=delay
                    )
                else:
                    task = parse_habr_vacancies_task.delay(
                        access_token=access_token,
                        pages=pages,
                        delay=delay,
                        get_details=get_details
                    )
                
                self.stdout.write(f"🚀 Задача Celery запущена с ID: {task.id}")
                
                if wait_for_result:
                    self.stdout.write("⏳ Ожидаем завершения задачи...")
                    result = task.get()
                    self.print_formatted_result(result)
                else:
                    self.stdout.write(
                        self.style.SUCCESS("✅ Задача отправлена в очередь Celery")
                    )
            else:
                # Запускаем синхронно
                if parse_all:
                    self.stdout.write("🔄 Начинаем парсинг всех вакансий...")
                    result = parse_habr_all_vacancies(
                        access_token=access_token,
                        pages=pages,
                        delay=delay,
                        get_details=get_details
                    )
                elif parse_archived:
                    self.stdout.write("🔄 Начинаем парсинг архивных вакансий...")
                    result = parse_habr_archived_vacancies(
                        access_token=access_token,
                        pages=pages,
                        delay=delay
                    )
                else:
                    self.stdout.write("🔄 Начинаем парсинг активных вакансий...")
                    result = parse_habr_vacancies(
                        access_token=access_token,
                        pages=pages,
                        delay=delay,
                        get_details=get_details
                    )
                
                self.print_formatted_result(result)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\n⚠️ Парсинг прерван пользователем")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка при выполнении парсинга: {e}")
            )
            if hasattr(e, '__traceback__'):
                import traceback
                self.stdout.write(f"🔍 Детали ошибки:")
                traceback.print_exc() 