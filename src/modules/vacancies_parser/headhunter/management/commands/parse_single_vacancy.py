from django.core.management.base import BaseCommand
from src.modules.vacancies_parser.headhunter.scripts import HeadHunterParser
from src.modules.vacancies_parser.headhunter.models import Vacancy
import time


class Command(BaseCommand):
    help = 'Парсинг одной вакансии с HeadHunter по ID'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'vacancy_id',
            type=str,
            help='ID вакансии на HeadHunter'
        )

        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Принудительно обновить существующую вакансию'
        )
    
    def handle(self, *args, **options):
        vacancy_id = options['vacancy_id']
        force_update = options['force_update']
        
        self.stdout.write(f'🚀 Парсинг вакансии с ID: {vacancy_id}')
        
        parser = HeadHunterParser()
        
        # Проверяем, существует ли уже вакансия
        existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
        if existing_vacancy and not force_update:
            self.stdout.write(
                f'⚠️  Вакансия с ID {vacancy_id} уже существует в базе данных.\n'
                f'Используйте --force-update для принудительного обновления.'
            )
            return
        
        # Получаем вакансию напрямую по ID
        self.stdout.write('📥 Получение вакансии по ID...')
        vacancy_data = parser.get_vacancy_details(vacancy_id)
        
        if not vacancy_data:
            self.stdout.write(f'❌ Вакансия с ID {vacancy_id} не найдена или недоступна')
            return
        
        # Проверяем структуру данных
        if not isinstance(vacancy_data, dict):
            self.stdout.write(f'❌ Неожиданный формат данных: {type(vacancy_data)}')
            return
            
        if 'id' not in vacancy_data:
            self.stdout.write(f'❌ В данных вакансии отсутствует ID')
            return
        
        self.stdout.write('✅ Вакансия получена')
        self.stdout.write(f'   • ID: {vacancy_data.get("id")}')
        self.stdout.write(f'   • Название: {vacancy_data.get("name", "Не указано")}')
        
        # Парсим вакансию
        self.stdout.write('🔍 Парсинг данных вакансии...')
        
        # Дополнительная диагностика
        self.stdout.write(f'   • Тип данных: {type(vacancy_data)}')
        self.stdout.write(f'   • Ключи: {list(vacancy_data.keys()) if isinstance(vacancy_data, dict) else "не словарь"}')
        
        # Проверяем потенциально проблемные поля
        problem_fields = ['address', 'snippet', 'professional_roles', 'salary', 'area', 'employer']
        for field in problem_fields:
            value = vacancy_data.get(field)
            self.stdout.write(f'   • {field}: {type(value)} - {value}')
        
        vacancy = parser.parse_vacancy(vacancy_data)
        
        if not vacancy:
            self.stdout.write('❌ Ошибка при парсинге вакансии')
            return
        
        # Выводим информацию о вакансии
        self.stdout.write(f'\n📋 Информация о вакансии:')
        self.stdout.write(f'   • Название: {vacancy.title}')
        self.stdout.write(f'   • Компания: {vacancy.company_name}')
        self.stdout.write(f'   • Город: {vacancy.city}')
        if vacancy.salary_from or vacancy.salary_to:
            salary_info = []
            if vacancy.salary_from:
                salary_info.append(f'от {vacancy.salary_from}')
            if vacancy.salary_to:
                salary_info.append(f'до {vacancy.salary_to}')
            if vacancy.salary_currency:
                salary_info.append(vacancy.salary_currency)
            self.stdout.write(f'   • Зарплата: {" ".join(salary_info)}')
        self.stdout.write(f'   • URL: {vacancy.url}')
        
        # Сохраняем или обновляем вакансию
        if existing_vacancy:
            if force_update:
                self.stdout.write('🔄 Обновление существующей вакансии...')
                
                # Проверяем, есть ли изменения
                new_data = {
                    'title': vacancy.title,
                    'company_name': vacancy.company_name,
                    'salary_from': vacancy.salary_from,
                    'salary_to': vacancy.salary_to,
                    'salary_currency': vacancy.salary_currency,
                    'city': vacancy.city,
                    'address': vacancy.address,
                    'description': vacancy.description,
                    'requirements': vacancy.requirements,
                    'responsibilities': vacancy.responsibilities,
                    'employment_type': vacancy.employment_type,
                    'experience_level': vacancy.experience_level,
                    'key_skills': vacancy.key_skills,
                    'schedule_type': vacancy.schedule_type,
                    'professional_role': vacancy.professional_role,
                    'employer_name': vacancy.employer_name,
                    'premium': vacancy.premium,
                    'has_test': vacancy.has_test,
                    'response_letter_required': vacancy.response_letter_required,
                }
                
                if existing_vacancy.has_changes(new_data):
                    # Создаем новую версию с историей изменений
                    existing_vacancy.create_version(new_data)
                    # Обновляем данные вакансии
                    for field, value in new_data.items():
                        setattr(existing_vacancy, field, value)
                    existing_vacancy.save()
                    self.stdout.write('✅ Вакансия обновлена (создана новая версия)')
                else:
                    self.stdout.write('ℹ️  Изменений не обнаружено')
            else:
                self.stdout.write('ℹ️  Вакансия уже существует, обновление не требуется')
        else:
            self.stdout.write('💾 Сохранение новой вакансии...')
            vacancy.save()
            self.stdout.write('✅ Вакансия успешно сохранена')
        
        self.stdout.write(f'\n🎉 Парсинг вакансии {vacancy_id} завершен!') 