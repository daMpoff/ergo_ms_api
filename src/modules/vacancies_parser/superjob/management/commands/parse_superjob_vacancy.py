import json
import os
from django.core.management.base import BaseCommand
from src.modules.vacancies_parser.superjob.scripts import get_vacancy_details
from src.modules.vacancies_parser.superjob.tasks import get_superjob_vacancy_details_task


class Command(BaseCommand):
    help = 'Получение детальной информации о конкретной вакансии SuperJob'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'vacancy_id',
            type=str,
            help='ID вакансии SuperJob'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='config.json',
            help='Путь к JSON конфигурационному файлу (по умолчанию config.json)'
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='API ключ SuperJob (переопределяет config)'
        )
        parser.add_argument(
            '--wait',
            action='store_true',
            help='Дождаться завершения задачи Celery и вывести результат'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Сохранить вакансию в базу данных'
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
    
    def print_vacancy_details(self, vacancy_data):
        """Вывод детальной информации о вакансии"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ВАКАНСИИ SUPERJOB'))
        self.stdout.write('='*60)
        
        if not vacancy_data:
            self.stdout.write(self.style.ERROR('Вакансия не найдена или недоступна'))
            return
        
        # Основная информация
        self.stdout.write(f"ID: {vacancy_data.get('id', 'Не указан')}")
        self.stdout.write(f"Название: {vacancy_data.get('profession', 'Не указано')}")
        self.stdout.write(f"Компания: {vacancy_data.get('firm_name', 'Не указана')}")
        
        # Зарплата
        payment_from = vacancy_data.get('payment_from')
        payment_to = vacancy_data.get('payment_to')
        currency = vacancy_data.get('currency', 'RUR')
        
        if payment_from or payment_to:
            if payment_from and payment_to:
                salary = f"{payment_from} - {payment_to} {currency}"
            elif payment_from:
                salary = f"от {payment_from} {currency}"
            else:
                salary = f"до {payment_to} {currency}"
            self.stdout.write(f"Зарплата: {salary}")
        else:
            self.stdout.write("Зарплата: Не указана")
        
        # Локация
        town = vacancy_data.get('town', {})
        if town and town.get('title'):
            self.stdout.write(f"Город: {town['title']}")
        
        address = vacancy_data.get('address')
        if address:
            self.stdout.write(f"Адрес: {address}")
        
        # Тип занятости
        type_of_work = vacancy_data.get('type_of_work', {})
        if type_of_work and type_of_work.get('title'):
            self.stdout.write(f"Тип занятости: {type_of_work['title']}")
        
        # Опыт
        experience = vacancy_data.get('experience', {})
        if experience and experience.get('title'):
            self.stdout.write(f"Опыт: {experience['title']}")
        
        # График работы
        place_of_work = vacancy_data.get('place_of_work', {})
        if place_of_work and place_of_work.get('title'):
            self.stdout.write(f"График работы: {place_of_work['title']}")
        
        # Описание
        candidat = vacancy_data.get('candidat')
        if candidat:
            self.stdout.write(f"\nОписание:\n{candidat}")
        
        # Требования
        requirement = vacancy_data.get('requirement')
        if requirement:
            self.stdout.write(f"\nТребования:\n{requirement}")
        
        # Обязанности
        responsibility = vacancy_data.get('responsibility')
        if responsibility:
            self.stdout.write(f"\nОбязанности:\n{responsibility}")
        
        # Ключевые навыки
        key_skills = vacancy_data.get('key_skills', [])
        if key_skills:
            skills_list = [skill.get('title', '') for skill in key_skills if skill.get('title')]
            if skills_list:
                self.stdout.write(f"\nКлючевые навыки: {', '.join(skills_list)}")
        
        # Ссылка
        link = vacancy_data.get('link')
        if link:
            self.stdout.write(f"\nСсылка на вакансию: {link}")
        
        # Дополнительная информация
        if vacancy_data.get('is_star'):
            self.stdout.write(self.style.SUCCESS("⭐ Премиум вакансия"))
        
        if vacancy_data.get('is_archive'):
            self.stdout.write(self.style.WARNING("📁 Архивная вакансия"))
        
        self.stdout.write('='*60 + '\n')
    
    def handle(self, *args, **options):
        vacancy_id = options['vacancy_id']
        
        # Загружаем конфигурацию
        config = self.load_config(options['config'])
        
        # Определяем API ключ
        api_key = options.get('api_key') or config.get('api_key')
        
        if not api_key:
            self.stdout.write(
                self.style.WARNING('API ключ SuperJob не указан. Получение деталей может быть ограничено.')
            )
        
        self.stdout.write(f'Получаем детали вакансии SuperJob с ID: {vacancy_id}')
        
        if options.get('wait'):
            # Синхронный режим
            vacancy_data = get_vacancy_details(vacancy_id, api_key)
            self.print_vacancy_details(vacancy_data)
            
            # Сохраняем в базу данных, если указан флаг
            if options.get('save') and vacancy_data:
                from src.modules.vacancies_parser.superjob.scripts import parse_vacancy_data, save_vacancy_to_db
                parsed_data = parse_vacancy_data(vacancy_data)
                vacancy = save_vacancy_to_db(parsed_data)
                if vacancy:
                    self.stdout.write(
                        self.style.SUCCESS(f'Вакансия сохранена в базу данных: {vacancy.title}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('Ошибка при сохранении вакансии в базу данных')
                    )
        else:
            # Асинхронный режим
            task = get_superjob_vacancy_details_task.delay(vacancy_id, api_key)
            self.stdout.write(f'Задача запущена. ID: {task.id}')
            
            if options.get('wait'):
                self.stdout.write('Ожидаем завершения задачи...')
                result = task.get()
                if result.get('status') == 'SUCCESS':
                    vacancy_data = result.get('result')
                    self.print_vacancy_details(vacancy_data)
                    
                    # Сохраняем в базу данных, если указан флаг
                    if options.get('save') and vacancy_data:
                        from src.modules.vacancies_parser.superjob.scripts import parse_vacancy_data, save_vacancy_to_db
                        parsed_data = parse_vacancy_data(vacancy_data)
                        vacancy = save_vacancy_to_db(parsed_data)
                        if vacancy:
                            self.stdout.write(
                                self.style.SUCCESS(f'Вакансия сохранена в базу данных: {vacancy.title}')
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR('Ошибка при сохранении вакансии в базу данных')
                            )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Ошибка при получении деталей вакансии: {result.get("error")}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS('Получение деталей вакансии SuperJob завершено!')
        ) 