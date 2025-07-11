from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from src.modules.crm.models import (
    Project, ProjectMember, Task, TaskComment, TimeLog,
    ProjectStatus, ProjectPriority, TaskStatus, TaskPriority
)
from django.utils import timezone
from datetime import datetime, timedelta
import datetime as dt
import random
from faker import Faker

User = get_user_model()
fake = Faker('ru_RU')

class Command(BaseCommand):
    help = 'Генерирует тестовые данные для CRM модуля с университетской тематикой на 2025 год'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Очистить существующие данные')
        parser.add_argument('--preserve-users', action='store_true', help='Сохранить всех пользователей при очистке (не удалять)')
        parser.add_argument('--users', type=int, default=15, help='Количество пользователей')
        parser.add_argument('--projects', type=int, default=10, help='Количество проектов')
        parser.add_argument('--tasks-per-project', type=int, default=8, help='Количество задач на проект')
        parser.add_argument('--user-id', type=int, default=1, help='ID пользователя, к которому будут привязаны все проекты и задачи')

    def handle(self, *args, **options):
        user_id = options['user_id']
        
        if options['clear']:
            self.clear_data(user_id, preserve_users=options['preserve_users'])
        
        # Убеждаемся, что указанный пользователь существует
        creator_user = self.ensure_creator_user(user_id)
        if not creator_user:
            return
        
        self.create_statuses_and_priorities()
        users = self.create_users(options['users'])
        projects = self.create_projects(users, options['projects'], creator_user)
        self.create_tasks_and_related_data(projects, users, options['tasks_per_project'], creator_user)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано:\n'
                f'- {len(users)} пользователей\n'
                f'- {len(projects)} проектов\n'
                f'- {Task.objects.count()} задач\n'
                f'- {TaskComment.objects.count()} комментариев\n'
                f'- {TimeLog.objects.count()} записей времени\n'
                f'- Все проекты и задачи привязаны к пользователю с ID {creator_user.id} ({creator_user.username})'
            )
        )

    def clear_data(self, preserve_user_id, preserve_users=False):
        """Очистка существующих данных"""
        self.stdout.write('Очистка существующих данных')
        
        TimeLog.objects.all().delete()
        TaskComment.objects.all().delete()
        Task.objects.all().delete()
        ProjectMember.objects.all().delete()
        Project.objects.all().delete()
        
        if not preserve_users:
            # Удаляем пользователей кроме суперпользователей и указанного пользователя
            User.objects.filter(is_superuser=False).exclude(id=preserve_user_id).delete()
            self.stdout.write('  - Пользователи удалены (кроме суперпользователей и ID {})'.format(preserve_user_id))
        else:
            self.stdout.write('  - Пользователи сохранены (использован параметр --preserve-users)')
        
        self.stdout.write(self.style.SUCCESS('Данные очищены'))

    def ensure_creator_user(self, user_id):
        """Убеждаемся, что пользователь с указанным ID существует"""
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f'Пользователь с ID {user_id} найден: {user.username}')
            return user
        except User.DoesNotExist:
            # Создаем пользователя с указанным ID
            try:
                user = User.objects.create(
                    id=user_id,
                    username=f'project_creator_{user_id}',
                    first_name='Создатель',
                    last_name='Проектов',
                    email=f'creator_{user_id}@university.edu',
                    is_staff=True
                )
                self.stdout.write(f'Создан пользователь с ID {user_id}: {user.username}')
                return user
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Не удалось создать пользователя с ID {user_id}: {e}\n'
                        f'Возможно, этот ID уже существует или недоступен.'
                    )
                )
                return None

    def create_statuses_and_priorities(self):
        """Создание статусов и приоритетов"""
        self.stdout.write('Создание статусов и приоритетов')
        
        # Статусы проектов
        project_statuses = [
            {'name': 'Планирование', 'code': 'planning', 'color': '#6c757d', 'order': 1, 'is_default': True},
            {'name': 'Активный', 'code': 'active', 'color': '#28a745', 'order': 2},
            {'name': 'Приостановлен', 'code': 'on_hold', 'color': '#ffc107', 'order': 3},
            {'name': 'Завершен', 'code': 'completed', 'color': '#007bff', 'order': 4, 'is_final': True},
            {'name': 'Отменен', 'code': 'cancelled', 'color': '#dc3545', 'order': 5, 'is_final': True},
        ]
        
        for status_data in project_statuses:
            ProjectStatus.objects.get_or_create(
                code=status_data['code'],
                defaults=status_data
            )
        
        # Приоритеты проектов
        project_priorities = [
            {'name': 'Низкий', 'code': 'low', 'color': '#6c757d', 'level': 1},
            {'name': 'Средний', 'code': 'medium', 'color': '#007bff', 'level': 2, 'is_default': True},
            {'name': 'Высокий', 'code': 'high', 'color': '#fd7e14', 'level': 3},
            {'name': 'Срочный', 'code': 'urgent', 'color': '#dc3545', 'level': 4},
        ]
        
        for priority_data in project_priorities:
            ProjectPriority.objects.get_or_create(
                code=priority_data['code'],
                defaults=priority_data
            )
        
        # Статусы задач
        task_statuses = [
            {'name': 'К выполнению', 'code': 'todo', 'color': '#6c757d', 'order': 1, 'is_default': True},
            {'name': 'В работе', 'code': 'in_progress', 'color': '#ffc107', 'order': 2},
            {'name': 'На проверке', 'code': 'review', 'color': '#17a2b8', 'order': 3},
            {'name': 'Выполнено', 'code': 'done', 'color': '#28a745', 'order': 4, 'is_final': True},
            {'name': 'Отменено', 'code': 'cancelled', 'color': '#dc3545', 'order': 5, 'is_final': True},
        ]
        
        for status_data in task_statuses:
            TaskStatus.objects.get_or_create(
                code=status_data['code'],
                defaults=status_data
            )
        
        # Приоритеты задач
        task_priorities = [
            {'name': 'Низкий', 'code': 'low', 'color': '#6c757d', 'level': 1},
            {'name': 'Средний', 'code': 'medium', 'color': '#007bff', 'level': 2, 'is_default': True},
            {'name': 'Высокий', 'code': 'high', 'color': '#fd7e14', 'level': 3},
            {'name': 'Срочный', 'code': 'urgent', 'color': '#dc3545', 'level': 4},
        ]
        
        for priority_data in task_priorities:
            TaskPriority.objects.get_or_create(
                code=priority_data['code'],
                defaults=priority_data
            )

    def create_users(self, count):
        """Создание пользователей"""
        self.stdout.write(f'Создание {count} пользователей')
        
        # Предопределенные пользователи
        predefined_users = [
            {'username': 'dekan_fit', 'first_name': 'Александр', 'last_name': 'Петров', 'email': 'dekan@university.edu'},
            {'username': 'zav_kafedroy', 'first_name': 'Елена', 'last_name': 'Сидорова', 'email': 'kafedra@university.edu'},
            {'username': 'prof_ivanov', 'first_name': 'Иван', 'last_name': 'Иванов', 'email': 'ivanov@university.edu'},
            {'username': 'doc_smirnova', 'first_name': 'Мария', 'last_name': 'Смирнова', 'email': 'smirnova@university.edu'},
            {'username': 'admin_kirov', 'first_name': 'Сергей', 'last_name': 'Киров', 'email': 'admin@university.edu'},
            {'username': 'student_popov', 'first_name': 'Алексей', 'last_name': 'Попов', 'email': 'popov@student.university.edu'},
            {'username': 'aspirant_kozlov', 'first_name': 'Анна', 'last_name': 'Козлова', 'email': 'kozlova@university.edu'},
        ]
        
        users = []
        
        # Создаем предопределенных пользователей
        for user_data in predefined_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'email': user_data['email'],
                }
            )
            users.append(user)
        
        # Создаем остальных пользователей
        for i in range(len(predefined_users), count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{fake.user_name()}_{i}"
            email = f"{username}@university.edu"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                }
            )
            users.append(user)
        
        return users

    def create_projects(self, users, count, creator_user):
        """Создание университетских проектов"""
        self.stdout.write(f'Создание {count} проектов от имени пользователя {creator_user.username} (ID: {creator_user.id})')
        
        # Шаблоны университетских проектов
        project_templates = [
            {
                'name': 'Разработка учебной программы "Искусственный интеллект"',
                'description': 'Создание современной учебной программы по ИИ с практическими проектами и лабораторными работами для студентов 3-4 курсов',
                'color': '#007bff'
            },
            {
                'name': 'Модернизация компьютерных классов',
                'description': 'Обновление оборудования и программного обеспечения в компьютерных классах факультета',
                'color': '#28a745'
            },
            {
                'name': 'Научная конференция "Цифровые технологии 2025"',
                'description': 'Организация ежегодной научной конференции с участием студентов, аспирантов и преподавателей',
                'color': '#fd7e14'
            },
            {
                'name': 'Система электронного документооборота',
                'description': 'Внедрение цифровой системы управления документами и процессами деканата',
                'color': '#6f42c1'
            },
            {
                'name': 'Разработка мобильного приложения "УниВерситет"',
                'description': 'Создание мобильного приложения для студентов с расписанием, оценками и новостями',
                'color': '#20c997'
            },
            {
                'name': 'Обновление сайта факультета',
                'description': 'Редизайн и техническое обновление официального сайта факультета информационных технологий',
                'color': '#e83e8c'
            },
            {
                'name': 'Программа стажировок в IT-компаниях',
                'description': 'Создание партнерской программы с ведущими IT-компаниями для стажировок студентов',
                'color': '#17a2b8'
            },
            {
                'name': 'Лаборатория кибербезопасности',
                'description': 'Создание специализированной лаборатории для изучения информационной безопасности',
                'color': '#dc3545'
            },
            {
                'name': 'Цифровизация библиотеки',
                'description': 'Перевод библиотечного фонда в цифровой формат и создание электронного каталога',
                'color': '#ffc107'
            },
            {
                'name': 'Международная программа обмена',
                'description': 'Развитие программы академической мобильности с зарубежными университетами',
                'color': '#6c757d'
            },
        ]
        
        projects = []
        statuses = list(ProjectStatus.objects.all())
        priorities = list(ProjectPriority.objects.all())
        
        for i in range(count):
            template = project_templates[i % len(project_templates)]
            
            # Даты проекта в 2025 году
            start_date = fake.date_between(
                start_date=datetime(2025, 1, 1).date(),
                end_date=datetime(2025, 6, 30).date()
            )
            end_date = fake.date_between(
                start_date=start_date + timedelta(days=30),
                end_date=datetime(2025, 12, 31).date()
            )
            
            project = Project.objects.create(
                name=template['name'] + (f" (Этап {i//len(project_templates) + 1})" if i >= len(project_templates) else ""),
                description=template['description'],
                owner=creator_user,  # Все проекты создаются указанным пользователем
                manager=random.choice(users),
                status=random.choice(['planning', 'active', 'on_hold']),
                priority=random.choice(['low', 'medium', 'high', 'urgent']),
                start_date=start_date,
                end_date=end_date,
                color=template['color'],
                status_ref=random.choice(statuses),
                priority_ref=random.choice(priorities)
            )
            
            # Добавляем участников команды
            team_size = random.randint(2, 6)
            team_members = random.sample(users, min(team_size, len(users)))
            
            for member in team_members:
                if member != project.owner and member != project.manager:
                    ProjectMember.objects.create(
                        project=project,
                        user=member,
                        role=random.choice(['member', 'lead', 'observer'])
                    )
            
            projects.append(project)
        
        return projects

    def create_tasks_and_related_data(self, projects, users, tasks_per_project, creator_user):
        """Создание задач и связанных данных"""
        self.stdout.write(f'Создание задач и связанных данных от имени пользователя {creator_user.username} (ID: {creator_user.id})')
        
        # Шаблоны задач для университетских проектов
        task_templates = [
            'Анализ требований',
            'Техническое планирование',
            'Разработка технического задания',
            'Создание прототипа',
            'Тестирование системы',
            'Подготовка документации',
            'Обучение пользователей',
            'Развертывание в продакшн',
            'Подготовка презентации',
            'Согласование с руководством',
            'Проведение совещания',
            'Анализ результатов',
            'Подготовка отчета',
            'Исследование технологий',
            'Создание макетов',
            'Настройка оборудования',
            'Интеграция с системами',
            'Проведение опроса',
            'Сбор обратной связи',
            'Оптимизация процессов'
        ]
        
        task_statuses = list(TaskStatus.objects.all())
        task_priorities = list(TaskPriority.objects.all())
        
        for project in projects:
            for i in range(tasks_per_project):
                task_name = random.choice(task_templates)
                
                # Даты задачи в рамках проекта
                task_start = fake.date_between(
                    start_date=project.start_date,
                    end_date=project.end_date - timedelta(days=7)
                )
                task_due = fake.date_between(
                    start_date=task_start + timedelta(days=1),
                    end_date=project.end_date
                )
                
                # Определяем исполнителя (владелец, менеджер или участник команды)
                possible_assignees = [project.owner, project.manager]
                team_members = project.memberships.all()
                possible_assignees.extend([m.user for m in team_members])
                assignee = random.choice(possible_assignees) if possible_assignees else None
                
                # Генерируем случайное время
                start_time = dt.time(
                    hour=random.randint(8, 18),
                    minute=random.choice([0, 15, 30, 45])
                )
                due_time = dt.time(
                    hour=random.randint(8, 18),
                    minute=random.choice([0, 15, 30, 45])
                )
                
                # Создаем timezone-aware datetime
                start_datetime = timezone.make_aware(datetime.combine(task_start, start_time))
                due_datetime = timezone.make_aware(datetime.combine(task_due, due_time))
                
                task = Task.objects.create(
                    title=f"{task_name} - {project.name[:30]}",
                    description=fake.text(max_nb_chars=200),
                    project=project,
                    assignee=assignee,
                    creator=creator_user,  # Все задачи создаются указанным пользователем
                    status=random.choice(['todo', 'in_progress', 'review', 'done']),
                    priority=random.choice(['low', 'medium', 'high', 'urgent']),
                    start_date=start_datetime,
                    due_date=due_datetime,
                    estimated_hours=random.randint(2, 40),
                    kanban_order=i,
                    status_ref=random.choice(task_statuses),
                    priority_ref=random.choice(task_priorities)
                )
                
                # Завершенные задачи получают дату завершения
                if task.status == 'done':
                    # Используем безопасный диапазон для даты завершения
                    completion_start = task.start_date
                    completion_end = min(task.due_date, timezone.now())
                    
                    if completion_start <= completion_end:
                        task.completed_at = fake.date_time_between(
                            start_date=completion_start,
                            end_date=completion_end,
                            tzinfo=timezone.get_current_timezone()
                        )
                    else:
                        task.completed_at = completion_start
                    task.save()
                
                # Создаем комментарии к задачам
                for _ in range(random.randint(0, 3)):
                    TaskComment.objects.create(
                        task=task,
                        author=random.choice(users),
                        content=fake.text(max_nb_chars=150)
                    )
                
                # Создаем записи времени для задач в работе или завершенных
                if task.status in ['in_progress', 'done', 'review']:
                    for _ in range(random.randint(1, 5)):
                        # Определяем безопасный диапазон дат
                        work_start_date = task.start_date.date()
                        work_end_date = min(
                            task.due_date.date(),
                            timezone.now().date()
                        )
                        
                        # Проверяем, что диапазон валидный
                        if work_start_date <= work_end_date:
                            work_date = fake.date_between(
                                start_date=work_start_date,
                                end_date=work_end_date
                            )
                        else:
                            # Если диапазон невалидный, используем дату начала
                            work_date = work_start_date
                        
                        TimeLog.objects.create(
                            task=task,
                            user=task.assignee or random.choice(users),
                            description=f"Работа над задачей: {random.choice(['анализ', 'разработка', 'тестирование', 'документирование', 'исправления'])}",
                            hours=round(random.uniform(0.5, 8.0), 1),
                            date=work_date
                        )

    def get_default_status_priority(self, model_class):
        """Получение статуса/приоритета по умолчанию"""
        try:
            return model_class.objects.filter(is_default=True).first() or model_class.objects.first()
        except:
            return None 