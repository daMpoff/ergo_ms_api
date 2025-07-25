from django.core.management.base import BaseCommand
from src.modules.vacancies_parser.headhunter.scripts import HeadHunterParser
from src.modules.vacancies_parser.headhunter.models import Vacancy
import sys
import time
from src.modules.vacancies_parser.headhunter.tasks import parse_single_vacancy_task
from celery.result import AsyncResult


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

        parser.add_argument(
            '--wait',
            action='store_true',
            help='Дождаться завершения задачи Celery и вывести результат'
        )
    
    def print_formatted_result(self, result):
        if not isinstance(result, dict):
            self.stdout.write(f'Результат: {result}')
            return
        status = result.get('status')
        message = result.get('message', '')
        self.stdout.write(f'\n📋 Статус: {status}')
        if message:
            self.stdout.write(f'   • {message}')
        # Если есть ключевые поля вакансии, выводим их
        for key in ['title', 'company_name', 'city', 'salary_from', 'salary_to', 'salary_currency', 'url']:
            if key in result:
                self.stdout.write(f'   • {key}: {result[key]}')

    def handle(self, *args, **options):
        vacancy_id = options['vacancy_id']
        force_update = options['force_update']
        task = parse_single_vacancy_task.delay(vacancy_id, force_update)
        self.stdout.write(f'🚀 Задача Celery отправлена! Task ID: {task.id}')
        if options.get('wait'):
            self.stdout.write('⏳ Ожидание завершения задачи...')
            spinner = ['|', '/', '-', '\\']
            i = 0
            while not task.ready():
                sys.stdout.write(f'\rВыполняется... {spinner[i % 4]}')
                sys.stdout.flush()
                time.sleep(2)
                i += 1
            sys.stdout.write('\r')
            if task.successful():
                result = task.get()
                self.stdout.write('✅ Задача завершена!')
                self.print_formatted_result(result)
            else:
                self.stdout.write(f'❌ Ошибка при выполнении задачи: {task.result}')
        else:
            self.stdout.write('Проверьте статус задачи через Celery Flower или Django shell.') 