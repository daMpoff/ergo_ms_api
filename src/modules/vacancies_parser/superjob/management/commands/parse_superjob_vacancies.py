import json
import os
import time
import sys
from django.core.management.base import BaseCommand
from src.modules.vacancies_parser.superjob.scripts import parse_vacancies_by_text, parse_all_vacancies
from src.modules.vacancies_parser.superjob.tasks import parse_superjob_vacancies_task
from celery.result import AsyncResult


class Command(BaseCommand):
    help = 'Парсинг вакансий с SuperJob'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            default='config.json',
            help='Путь к JSON конфигурационному файлу (по умолчанию config.json)'
        )
        parser.add_argument(
            '--text',
            type=str,
            nargs='+',  # Позволяет указывать несколько слов
            help='Текст для поиска вакансий (можно указать несколько слов, переопределяет config)'
        )
        parser.add_argument(
            '--town',
            type=str,
            help='Город для поиска (переопределяет config)'
        )
        parser.add_argument(
            '--experience',
            type=str,
            choices=['noExperience', 'between1And3', 'between3And6', 'moreThan6'],
            help='Уровень опыта'
        )
        parser.add_argument(
            '--employment',
            type=str,
            choices=['full', 'part', 'project', 'volunteer', 'probation'],
            help='Тип занятости'
        )
        parser.add_argument(
            '--schedule',
            type=str,
            choices=['fullDay', 'shift', 'flexible', 'remote', 'flyInFlyOut'],
            help='График работы'
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
            '--universal',
            action='store_true',
            help='Универсальный парсинг всех вакансий по популярным запросам'
        )
        parser.add_argument(
            '--pages-per-query',
            type=int,
            help='Количество страниц для каждого запроса (переопределяет config)'
        )
        parser.add_argument(
            '--max-total-pages',
            type=int,
            help='Максимальное общее количество страниц (переопределяет config)'
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
            '--api-key',
            type=str,
            help='API ключ SuperJob (переопределяет config)'
        )
    
    def load_config(self, config_path):
        """Загрузка конфигурации из JSON файла"""
        try:
            # Получаем абсолютный путь к конфигурационному файлу
            if not os.path.isabs(config_path):
                # Получаем путь к директории команды
                command_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(command_dir, config_path)
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING(f'Конфигурационный файл {config_path} не найден. Используем значения по умолчанию.')
            )
            return {}
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при чтении конфигурационного файла {config_path}: {e}')
            )
            return {}
    
    def print_formatted_result(self, result):
        """Вывод отформатированного результата"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('РЕЗУЛЬТАТЫ ПАРСИНГА SUPERJOB'))
        self.stdout.write('='*50)
        
        if 'search_query' in result:
            self.stdout.write(f"Поисковый запрос: {result['search_query']}")
        
        self.stdout.write(f"Всего вакансий найдено: {result.get('total_vacancies', 0)}")
        self.stdout.write(f"Новых вакансий сохранено: {result.get('saved_vacancies', 0)}")
        self.stdout.write(f"Вакансий обновлено: {result.get('updated_vacancies', 0)}")
        self.stdout.write(f"Ошибок: {result.get('errors', 0)}")
        
        if 'total_queries' in result:
            self.stdout.write(f"Обработано запросов: {result.get('queries_processed', 0)}")
            self.stdout.write(f"Запросов с ошибками: {result.get('queries_failed', 0)}")
        
        self.stdout.write('='*50 + '\n')
    
    def handle(self, *args, **options):
        # Загружаем конфигурацию
        config = self.load_config(options['config'])
        
        # Определяем параметры парсинга
        api_key = options.get('api_key') or config.get('api_key')
        town = options.get('town') or config.get('town')
        experience = options.get('experience') or config.get('experience')
        employment = options.get('employment') or config.get('employment')
        schedule = options.get('schedule') or config.get('schedule')
        max_pages = options.get('pages') or config.get('max_pages', 5)
        delay = options.get('delay') or config.get('delay', 1.0)
        
        # Проверяем, есть ли API ключ
        if not api_key:
            self.stdout.write(
                self.style.WARNING('API ключ SuperJob не указан. Парсинг может быть ограничен.')
            )
        
        # Определяем режим парсинга
        if options.get('universal'):
            # Универсальный парсинг
            self.stdout.write('Запускаем универсальный парсинг вакансий SuperJob...')
            
            universal_config = config.get('universal_parsing', {})
            max_pages_per_query = options.get('pages_per_query') or universal_config.get('max_pages_per_query', 3)
            universal_delay = options.get('delay') or universal_config.get('delay', 1.0)
            
            if options.get('wait'):
                # Синхронный режим
                result = parse_all_vacancies(
                    max_pages_per_query=max_pages_per_query,
                    delay=universal_delay,
                    api_key=api_key
                )
                self.print_formatted_result(result)
            else:
                # Асинхронный режим
                from src.modules.vacancies_parser.superjob.tasks import parse_all_superjob_vacancies_task
                task = parse_all_superjob_vacancies_task.delay(
                    max_pages_per_query=max_pages_per_query,
                    delay=universal_delay,
                    api_key=api_key
                )
                self.stdout.write(f'Задача запущена. ID: {task.id}')
                
                if options.get('wait'):
                    self.stdout.write('Ожидаем завершения задачи...')
                    result = task.get()
                    self.print_formatted_result(result.get('result', {}))
        
        else:
            # Парсинг по текстовому запросу
            if options.get('text'):
                # Используем текст из аргументов командной строки
                search_texts = options['text']
            elif not options.get('use_config_only') and config.get('search_queries'):
                # Используем запросы из конфигурации
                search_texts = config['search_queries']
            else:
                # Запрашиваем у пользователя
                search_text = input('Введите текст для поиска вакансий: ')
                search_texts = [search_text] if search_text else ['Python']
            
            for text in search_texts:
                self.stdout.write(f'Парсим вакансии по запросу: "{text}"')
                
                if options.get('wait'):
                    # Синхронный режим
                    result = parse_vacancies_by_text(
                        text=text,
                        town=town,
                        experience=experience,
                        employment=employment,
                        schedule=schedule,
                        max_pages=max_pages,
                        delay=delay,
                        api_key=api_key
                    )
                    self.print_formatted_result(result)
                else:
                    # Асинхронный режим
                    task = parse_superjob_vacancies_task.delay(
                        text=text,
                        town=town,
                        experience=experience,
                        employment=employment,
                        schedule=schedule,
                        max_pages=max_pages,
                        delay=delay,
                        api_key=api_key
                    )
                    self.stdout.write(f'Задача запущена. ID: {task.id}')
                    
                    if options.get('wait'):
                        self.stdout.write('Ожидаем завершения задачи...')
                        result = task.get()
                        self.print_formatted_result(result.get('result', {}))
        
        self.stdout.write(
            self.style.SUCCESS('Парсинг вакансий SuperJob завершен!')
        ) 