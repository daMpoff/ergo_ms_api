import json
import os
import time
from django.core.management.base import BaseCommand
from src.modules.vacancies_parser.headhunter.scripts import parse_vacancies_by_text, parse_all_vacancies


class Command(BaseCommand):
    help = 'Парсинг вакансий с HeadHunter'
    
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
            '--area',
            type=int,
            help='ID региона (переопределяет config)'
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
            help='Универсальный парсинг всех вакансий по регионам и ролям'
        )
        parser.add_argument(
            '--pages-per-area',
            type=int,
            help='Количество страниц для каждого региона (переопределяет config)'
        )
        parser.add_argument(
            '--max-total-pages',
            type=int,
            help='Максимальное общее количество страниц (переопределяет config)'
        )
        parser.add_argument(
            '--areas-only',
            action='store_true',
            help='Парсить только по регионам (без профессиональных ролей)'
        )
        parser.add_argument(
            '--use-config-only',
            action='store_true',
            help='Использовать только настройки из конфигурационного файла'
        )
    
    def load_config(self, config_path):
        """Загрузка конфигурации из JSON файла"""
        try:
            # Получаем абсолютный путь к конфигурационному файлу
            if not os.path.isabs(config_path):
                # Если путь относительный, ищем файл в той же папке, где находится команда
                command_dir = os.path.dirname(__file__)
                config_path = os.path.join(command_dir, config_path)
            
            if not os.path.exists(config_path):
                self.stdout.write(
                    f'⚠️  Конфигурационный файл не найден: {config_path}'
                )
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.stdout.write(
                f'✅ Конфигурация загружена из: {config_path}'
            )
            return config
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                f'❌ Ошибка парсинга JSON файла: {e}'
            )
            return None
        except Exception as e:
            self.stdout.write(
                f'❌ Ошибка загрузки конфигурации: {e}'
            )
            return None
    
    def handle(self, *args, **options):
        # Загружаем конфигурацию
        config = self.load_config(options.get('config'))
        
        if not config and options.get('use_config_only'):
            self.stdout.write(
                '❌ Не удалось загрузить конфигурацию, а флаг --use-config-only установлен'
            )
            return
        
        # Определяем параметры парсинга
        if options.get('use_config_only') and config:
            # Используем только конфигурацию
            text_list = config.get('search_queries', [])
            area = config.get('area_code', 113)
            pages = config.get('parsing_settings', {}).get('pages_per_query', 2)
            delay = config.get('parsing_settings', {}).get('delay_between_queries', 1.0)
            get_details = config.get('parsing_settings', {}).get('get_detailed_info', True)
            universal = config.get('universal_parsing', {}).get('enabled', False)
            pages_per_area = config.get('universal_parsing', {}).get('pages_per_area', 5)
            max_total_pages = config.get('universal_parsing', {}).get('max_total_pages', 100)
            areas_only = config.get('universal_parsing', {}).get('areas_only', False)
        else:
            # Используем аргументы командной строки с fallback на конфигурацию
            text_list = options.get('text')
            area = options.get('area') or (config.get('area_code', 113) if config else 113)
            pages = options.get('pages') or (config.get('parsing_settings', {}).get('pages_per_query', 2) if config else 2)
            delay = options.get('delay') or (config.get('parsing_settings', {}).get('delay_between_queries', 1.0) if config else 1.0)
            get_details = not options.get('no_details') if options.get('no_details') is not None else (config.get('parsing_settings', {}).get('get_detailed_info', True) if config else True)
            universal = options.get('universal') or (config.get('universal_parsing', {}).get('enabled', False) if config else False)
            pages_per_area = options.get('pages_per_area') or (config.get('universal_parsing', {}).get('pages_per_area', 5) if config else 5)
            max_total_pages = options.get('max_total_pages') or (config.get('universal_parsing', {}).get('max_total_pages', 100) if config else 100)
            areas_only = options.get('areas_only') or (config.get('universal_parsing', {}).get('areas_only', False) if config else False)
        
        # Если не указан текст и не включен универсальный парсинг, используем конфигурацию
        if not text_list and not universal and config:
            text_list = config.get('search_queries', [])
            universal = config.get('universal_parsing', {}).get('enabled', False)
        
        if universal:
            # Универсальный парсинг всех вакансий
            self.stdout.write(
                f'🚀 Запуск универсального парсинга всех вакансий...\n'
                f'Страниц на регион: {pages_per_area}\n'
                f'Задержка: {delay} сек\n'
                f'Максимум страниц: {max_total_pages}\n'
                f'Только регионы: {areas_only}'
            )
            
            result = parse_all_vacancies(
                pages_per_area=pages_per_area,
                delay=delay,
                max_total_pages=max_total_pages,
                areas_only=areas_only
            )
            
            self.stdout.write(
                f'\n🎉 Универсальный парсинг завершен!\n'
                f'📊 Статистика:\n'
                f'   • Обработано регионов: {result["areas_processed"]}\n'
                f'   • Обработано ролей: {result["roles_processed"]}\n'
                f'   • Обработано страниц: {result["pages_processed"]}\n'
                f'   • Всего вакансий: {result["total_vacancies"]}\n'
                f'   • Новых вакансий: {result["new_vacancies"]}\n'
                f'   • Обновлено вакансий: {result["updated_vacancies"]}\n'
                f'   • Всего в базе: {result["total_in_db"]}'
            )
            
        elif text_list:
            # Парсинг по текстовым запросам
            self.stdout.write(
                f'🚀 Запуск парсинга по запросам: {text_list}\n'
                f'Регион: {area}\n'
                f'Страниц на запрос: {pages}\n'
                f'Задержка: {delay} сек\n'
                f'Детальная информация: {get_details}'
            )
            
            result = parse_vacancies_by_text(
                text_list=text_list,
                area=area,
                pages=pages,
                delay=delay,
                get_details=get_details
            )
            
            self.stdout.write(
                f'\n🎉 Парсинг завершен!\n'
                f'📊 Статистика:\n'
                f'   • Всего вакансий: {result["total_vacancies"]}\n'
                f'   • Новых вакансий: {result["new_vacancies"]}\n'
                f'   • Обновлено вакансий: {result["updated_vacancies"]}\n'
                f'   • Всего в базе: {result["total_in_db"]}'
            )
            
        else:
            self.stdout.write(
                '❌ Необходимо указать --text для поиска по запросам, --universal для универсального парсинга '
                'или настроить конфигурационный файл'
            ) 