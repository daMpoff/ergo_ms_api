from django.core.management.base import BaseCommand

from src.modules.crm.models import TaskStatus, TaskPriority


class Command(BaseCommand):
    help = 'Создает базовые статусы и приоритеты задач'

    def handle(self, *args, **options):
        self.stdout.write('Создание базовых статусов задач...')
        
        # Создаем базовые статусы задач
        statuses = [
            {
                'name': 'К выполнению',
                'code': 'todo',
                'color': '#6c757d',
                'order': 0,
                'is_default': True,
                'is_active': True
            },
            {
                'name': 'В работе',
                'code': 'in_progress',
                'color': '#17a2b8',
                'order': 1,
                'is_active': True
            },
            {
                'name': 'На проверке',
                'code': 'review',
                'color': '#ffc107',
                'order': 2,
                'is_active': True
            },
            {
                'name': 'Выполнено',
                'code': 'done',
                'color': '#28a745',
                'order': 3,
                'is_active': True,
                'is_final': True
            }
        ]
        
        for status_data in statuses:
            status, created = TaskStatus.objects.get_or_create(
                code=status_data['code'],
                defaults=status_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Создан статус: {status.name}')
                )
            else:
                self.stdout.write(f'Статус уже существует: {status.name}')
        
        # Создаем базовые приоритеты задач
        self.stdout.write('Создание базовых приоритетов задач...')
        
        priorities = [
            {
                'name': 'Низкий',
                'code': 'low',
                'color': '#6c757d',
                'level': 1,
                'is_active': True
            },
            {
                'name': 'Средний',
                'code': 'medium',
                'color': '#007bff',
                'level': 2,
                'is_default': True,
                'is_active': True
            },
            {
                'name': 'Высокий',
                'code': 'high',
                'color': '#fd7e14',
                'level': 3,
                'is_active': True
            },
            {
                'name': 'Срочный',
                'code': 'urgent',
                'color': '#dc3545',
                'level': 4,
                'is_active': True
            }
        ]
        
        for priority_data in priorities:
            priority, created = TaskPriority.objects.get_or_create(
                code=priority_data['code'],
                defaults=priority_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Создан приоритет: {priority.name}')
                )
            else:
                self.stdout.write(f'Приоритет уже существует: {priority.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Базовые статусы и приоритеты созданы!')
        ) 