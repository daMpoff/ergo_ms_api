from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Генерирует тестовые данные для LMS системы с IT курсами'

    def get_models(self):
        """Импорт моделей только когда нужно"""
        from src.modules.lms.models import (
            Subject, CourseCategory, CourseFormat, Theme, Lesson, 
            Test, Question, Answer, Assignment, UserRole, Teacher, 
            Student, StudentGroup, Enrollment, UserProfile, Resource,
            TestBank, Badge, UserBadge, StudentAnswerSelection, StudentAnswer,
            TestAttempt, SubmittedAssignment, PrivateMessage, Notification,
            ForumPost, ForumDiscussion, Forum, CourseFile, CalendarEvent,
            Grade
        )
        return {
            'Subject': Subject,
            'CourseCategory': CourseCategory,
            'CourseFormat': CourseFormat,
            'Theme': Theme,
            'Lesson': Lesson,
            'Test': Test,
            'Question': Question,
            'Answer': Answer,
            'Assignment': Assignment,
            'UserRole': UserRole,
            'Teacher': Teacher,
            'Student': Student,
            'StudentGroup': StudentGroup,
            'Enrollment': Enrollment,
            'UserProfile': UserProfile,
            'Resource': Resource,
            'TestBank': TestBank,
            'Badge': Badge,
            'UserBadge': UserBadge,
            'StudentAnswerSelection': StudentAnswerSelection,
            'StudentAnswer': StudentAnswer,
            'TestAttempt': TestAttempt,
            'SubmittedAssignment': SubmittedAssignment,
            'PrivateMessage': PrivateMessage,
            'Notification': Notification,
            'ForumPost': ForumPost,
            'ForumDiscussion': ForumDiscussion,
            'Forum': Forum,
            'CourseFile': CourseFile,
            'CalendarEvent': CalendarEvent,
            'Grade': Grade
        }

    def add_arguments(self, parser):
        parser.add_argument(
            '--courses',
            type=int,
            default=10,
            help='Количество курсов для создания'
        )
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Количество пользователей для создания'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие данные перед генерацией'
        )
        parser.add_argument(
            '--preserve-users', 
            action='store_true', 
            help='Сохранить всех пользователей при очистке (не удалять)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Команда для генерации данных LMS системы')

        if options['clear']:
            self.stdout.write('Очистка существующих данных...')
            self.clear_data(preserve_users=options['preserve_users'])

        self.stdout.write('Создание категорий курсов...')
        categories = self.create_categories()
        
        self.stdout.write('Создание форматов курсов...')
        formats = self.create_formats()
        
        self.stdout.write('Создание пользователей...')
        users = self.create_users(options['users'])
        
        self.stdout.write('Создание групп студентов...')
        groups = self.create_student_groups(users['teachers'])
        
        self.stdout.write('Создание студентов...')
        students = self.create_students(users['students'], groups)
        
        self.stdout.write('Создание IT курсов...')
        subjects = self.create_it_courses(categories, formats, users['teachers'], options['courses'])
        
        self.stdout.write('Создание тем и уроков...')
        self.create_themes_and_lessons(subjects)
        
        self.stdout.write('Создание тестов и заданий...')
        self.create_tests_and_assignments(subjects)
        
        self.stdout.write('Создание записей на курсы...')
        self.create_enrollments(subjects, users['students'])
        
        self.stdout.write('Создание значков...')
        self.create_badges(subjects)

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано:\n'
                f'- Курсов: {len(subjects)}\n'
                f'- Пользователей: {len(users["all"])}\n'
                f'- Категорий: {len(categories)}\n'
                f'- Форматов: {len(formats)}'
            )
        )

    def clear_data(self, preserve_users=False):
        """Очистка существующих данных"""
        models = self.get_models()
        
        # Удаляем в правильном порядке, учитывая зависимости
        self.stdout.write('  - Удаление результатов тестов и заданий...')
        models['UserBadge'].objects.all().delete()
        models['StudentAnswerSelection'].objects.all().delete()
        models['StudentAnswer'].objects.all().delete()
        models['TestAttempt'].objects.all().delete()
        models['SubmittedAssignment'].objects.all().delete()
        
        self.stdout.write('  - Удаление коммуникаций...')
        models['PrivateMessage'].objects.all().delete()
        models['Notification'].objects.all().delete()
        models['ForumPost'].objects.all().delete()
        models['ForumDiscussion'].objects.all().delete()
        models['Forum'].objects.all().delete()
        
        self.stdout.write('  - Удаление контента курсов...')
        models['Answer'].objects.all().delete()
        models['Question'].objects.all().delete()
        models['Test'].objects.all().delete()
        models['Assignment'].objects.all().delete()
        models['Resource'].objects.all().delete()
        models['CourseFile'].objects.all().delete()
        models['Lesson'].objects.all().delete()
        models['Theme'].objects.all().delete()
        models['CalendarEvent'].objects.all().delete()
        
        self.stdout.write('  - Удаление записей на курсы...')
        models['Enrollment'].objects.all().delete()
        models['Grade'].objects.all().delete()
        
        self.stdout.write('  - Удаление курсов...')
        models['Subject'].objects.all().delete()
        models['TestBank'].objects.all().delete()
        models['Badge'].objects.all().delete()
        
        self.stdout.write('  - Удаление пользователей и групп...')
        models['Student'].objects.all().delete()
        models['Teacher'].objects.all().delete()
        models['StudentGroup'].objects.all().delete()
        models['UserProfile'].objects.all().delete()
        models['UserRole'].objects.all().delete()
        
        if not preserve_users:
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write('  - Пользователи удалены (кроме суперпользователей)')
        else:
            self.stdout.write('  - Пользователи сохранены (использован параметр --preserve-users)')
        
        self.stdout.write('  - Удаление категорий и форматов...')
        models['CourseCategory'].objects.all().delete()
        models['CourseFormat'].objects.all().delete()

    def create_categories(self):
        """Создание категорий IT курсов"""
        models = self.get_models()
        categories_data = [
            {
                'name': 'Веб-разработка',
                'description': 'Курсы по созданию веб-сайтов и веб-приложений',
                'subcategories': [
                    {'name': 'Frontend разработка', 'description': 'HTML, CSS, JavaScript, React, Vue.js'},
                    {'name': 'Backend разработка', 'description': 'Python, Django, Node.js, PHP'},
                    {'name': 'Full-stack разработка', 'description': 'Комплексная веб-разработка'},
                ]
            },
            {
                'name': 'Мобильная разработка',
                'description': 'Разработка мобильных приложений',
                'subcategories': [
                    {'name': 'Android разработка', 'description': 'Java, Kotlin, Android Studio'},
                    {'name': 'iOS разработка', 'description': 'Swift, Objective-C, Xcode'},
                    {'name': 'Кроссплатформенная разработка', 'description': 'React Native, Flutter'},
                ]
            },
            {
                'name': 'Data Science',
                'description': 'Анализ данных и машинное обучение',
                'subcategories': [
                    {'name': 'Машинное обучение', 'description': 'ML алгоритмы и модели'},
                    {'name': 'Анализ данных', 'description': 'Python, R, статистика'},
                    {'name': 'Большие данные', 'description': 'Hadoop, Spark, NoSQL'},
                ]
            },
            {
                'name': 'DevOps и инфраструктура',
                'description': 'Автоматизация и управление инфраструктурой',
                'subcategories': [
                    {'name': 'Контейнеризация', 'description': 'Docker, Kubernetes'},
                    {'name': 'CI/CD', 'description': 'Jenkins, GitLab CI, GitHub Actions'},
                    {'name': 'Облачные технологии', 'description': 'AWS, Azure, Google Cloud'},
                ]
            },
            {
                'name': 'Базы данных',
                'description': 'Проектирование и управление базами данных',
                'subcategories': [
                    {'name': 'SQL базы данных', 'description': 'MySQL, PostgreSQL, Oracle'},
                    {'name': 'NoSQL базы данных', 'description': 'MongoDB, Redis, Cassandra'},
                ]
            },
            {
                'name': 'Кибербезопасность',
                'description': 'Защита информации и систем',
                'subcategories': [
                    {'name': 'Этичный хакинг', 'description': 'Пентестинг и анализ уязвимостей'},
                    {'name': 'Сетевая безопасность', 'description': 'Защита сетевой инфраструктуры'},
                ]
            }
        ]

        categories = []
        for cat_data in categories_data:
            parent_cat = models['CourseCategory'].objects.create(
                name=cat_data['name'],
                description=cat_data['description'],
                sort_order=len(categories)
            )
            categories.append(parent_cat)
            
            for i, subcat_data in enumerate(cat_data['subcategories']):
                subcat = models['CourseCategory'].objects.create(
                    name=subcat_data['name'],
                    description=subcat_data['description'],
                    parent=parent_cat,
                    sort_order=i
                )
                categories.append(subcat)

        return categories

    def create_formats(self):
        """Создание форматов курсов"""
        models = self.get_models()
        formats_data = [
            {'name': 'Базовый курс', 'description': 'Основательное изучение с нуля'},
            {'name': 'Интенсив', 'description': 'Быстрое погружение в тему'},
            {'name': 'Практикум', 'description': 'Практические задания и проекты'},
            {'name': 'Мастер-класс', 'description': 'Углубленное изучение конкретных техник'},
            {'name': 'Онлайн-курс', 'description': 'Самостоятельное изучение'},
            {'name': 'Вебинар', 'description': 'Живые онлайн-занятия'},
        ]

        formats = []
        for format_data in formats_data:
            course_format = models['CourseFormat'].objects.create(**format_data)
            formats.append(course_format)

        return formats

    def create_users(self, count):
        """Создание пользователей: преподавателей и студентов"""
        models = self.get_models()
        teachers_count = max(5, count // 10)  # 10% преподавателей
        students_count = count - teachers_count

        # Создание преподавателей
        teachers = []
        teacher_names = [
            ('Иван', 'Петров'), ('Мария', 'Сидорова'), ('Алексей', 'Козлов'),
            ('Елена', 'Васильева'), ('Дмитрий', 'Смирнов'), ('Анна', 'Морозова'),
            ('Сергей', 'Соколов'), ('Ольга', 'Новикова'), ('Михаил', 'Лебедев'),
            ('Татьяна', 'Волкова')
        ]

        for i in range(teachers_count):
            first_name, last_name = teacher_names[i % len(teacher_names)]
            username = f"lms_teacher_{i+1}"
            email = f"{username}@lms.example.com"
            
            # Проверяем, что пользователя с таким username нет
            if User.objects.filter(username=username).exists():
                continue
                
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name,
            )
            
            # Создание профиля
            models['UserProfile'].objects.get_or_create(
                user=user,
                defaults={
                    'bio': f"Опытный преподаватель в области IT с {random.randint(3, 15)} летним стажем",
                    'city': random.choice(['Москва', 'Санкт-Петербург', 'Новосибирск', 'Казань']),
                    'phone': f"+7{random.randint(1000000000, 9999999999)}"
                }
            )
            
            # Роль преподавателя
            models['UserRole'].objects.create(user=user, role='teacher')
            
            # Создание преподавателя
            models['Teacher'].objects.create(
                user=user,
                department=random.choice([
                    'Кафедра информационных технологий',
                    'Кафедра программной инженерии',
                    'Кафедра компьютерных наук',
                    'Кафедра кибербезопасности'
                ]),
                academic_degree=random.choice([
                    'Кандидат технических наук',
                    'Доктор технических наук',
                    'Магистр информатики',
                    'Бакалавр компьютерных наук'
                ])
            )
            
            teachers.append(user)

        # Создание студентов
        students = []
        student_names = [
            ('Александр', 'Иванов'), ('Екатерина', 'Петрова'), ('Максим', 'Сидоров'),
            ('Анастасия', 'Козлова'), ('Артем', 'Васильев'), ('Дарья', 'Смирнова'),
            ('Никита', 'Соколов'), ('Валерия', 'Новикова'), ('Егор', 'Лебедев'),
            ('София', 'Волкова'), ('Данила', 'Морозов'), ('Полина', 'Орлова')
        ]

        for i in range(students_count):
            first_name, last_name = student_names[i % len(student_names)]
            username = f"lms_student_{i+1}"
            email = f"{username}@lms.example.com"
            
            # Проверяем, что пользователя с таким username нет
            if User.objects.filter(username=username).exists():
                continue
                
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name,
            )
            
            # Создание профиля
            models['UserProfile'].objects.get_or_create(
                user=user,
                defaults={
                    'bio': f"Студент, изучающий IT технологии",
                    'city': random.choice(['Москва', 'Санкт-Петербург', 'Новосибирск', 'Казань']),
                    'phone': f"+7{random.randint(1000000000, 9999999999)}"
                }
            )
            
            # Роль студента
            models['UserRole'].objects.create(user=user, role='student')
            
            students.append(user)

        return {
            'teachers': teachers,
            'students': students,
            'all': teachers + students
        }

    def create_student_groups(self, teachers):
        """Создание групп студентов"""
        models = self.get_models()
        groups_data = [
            {'name': 'ИТ-21-1', 'specialization': 'Информационные технологии', 'year': 2},
            {'name': 'ПИ-22-1', 'specialization': 'Программная инженерия', 'year': 1},
            {'name': 'ИБ-20-1', 'specialization': 'Информационная безопасность', 'year': 3},
            {'name': 'ИИ-21-2', 'specialization': 'Искусственный интеллект', 'year': 2},
        ]

        groups = []
        for group_data in groups_data:
            teacher_user = random.choice(teachers)
            teacher = models['Teacher'].objects.get(user=teacher_user)
            
            group = models['StudentGroup'].objects.create(
                name=group_data['name'],
                curator=teacher,
                specialization=group_data['specialization'],
                year_of_study=group_data['year']
            )
            groups.append(group)

        return groups

    def create_students(self, student_users, groups):
        """Создание записей студентов"""
        models = self.get_models()
        students = []
        for i, user in enumerate(student_users):
            group = groups[i % len(groups)]
            student = models['Student'].objects.create(
                user=user,
                group=group,
                student_id=f"ST{2020 + group.year_of_study}{i+1:04d}",
                enrollment_date=timezone.now().date() - timedelta(days=random.randint(30, 365))
            )
            students.append(student)

        return students

    def create_it_courses(self, categories, formats, teachers, count):
        """Создание IT курсов"""
        models = self.get_models()
        courses_data = [
            {
                'name': 'Основы Python разработки',
                'description': 'Изучение основ программирования на Python с нуля',
                'category_keywords': ['backend', 'анализ'],
                'summary': 'Курс для начинающих разработчиков. Изучите синтаксис Python, основы ООП, работу с библиотеками.',
            },
            {
                'name': 'React.js для начинающих',
                'description': 'Создание интерактивных пользовательских интерфейсов',
                'category_keywords': ['frontend'],
                'summary': 'Изучите современную библиотеку React для создания динамических веб-приложений.',
            },
            {
                'name': 'Django Framework',
                'description': 'Разработка веб-приложений на Django',
                'category_keywords': ['backend'],
                'summary': 'Создание полноценных веб-приложений с помощью популярного Python фреймворка.',
            },
            {
                'name': 'Машинное обучение с Python',
                'description': 'Введение в ML алгоритмы и библиотеки',
                'category_keywords': ['машинное', 'анализ'],
                'summary': 'Освойте основы машинного обучения, работу с scikit-learn, pandas и numpy.',
            },
            {
                'name': 'JavaScript ES6+',
                'description': 'Современный JavaScript и его возможности',
                'category_keywords': ['frontend'],
                'summary': 'Изучите современные возможности JavaScript: arrow functions, async/await, модули.',
            },
            {
                'name': 'Docker и контейнеризация',
                'description': 'Основы работы с контейнерами',
                'category_keywords': ['контейнеризация', 'devops'],
                'summary': 'Изучите Docker, создание образов, работу с Docker Compose и оркестрацию.',
            },
            {
                'name': 'SQL и базы данных',
                'description': 'Проектирование и работа с реляционными БД',
                'category_keywords': ['sql'],
                'summary': 'Основы SQL, проектирование баз данных, оптимизация запросов.',
            },
            {
                'name': 'Vue.js разработка',
                'description': 'Создание SPA приложений на Vue.js',
                'category_keywords': ['frontend'],
                'summary': 'Изучите прогрессивный фреймворк Vue.js для создания современных веб-приложений.',
            },
            {
                'name': 'Node.js Backend',
                'description': 'Серверная разработка на JavaScript',
                'category_keywords': ['backend'],
                'summary': 'Создание REST API и веб-серверов с помощью Node.js и Express.',
            },
            {
                'name': 'Git и система контроля версий',
                'description': 'Эффективная работа с Git',
                'category_keywords': ['devops'],
                'summary': 'Изучите Git: ветвление, слияние, работа в команде, GitHub/GitLab.',
            },
            {
                'name': 'Основы кибербезопасности',
                'description': 'Защита информации и систем',
                'category_keywords': ['безопасность', 'этичный'],
                'summary': 'Основы информационной безопасности, анализ уязвимостей, методы защиты.',
            },
            {
                'name': 'MongoDB и NoSQL',
                'description': 'Работа с документоориентированными БД',
                'category_keywords': ['nosql'],
                'summary': 'Изучите MongoDB: схемы данных, запросы, агрегация, индексирование.',
            },
            {
                'name': 'Android разработка на Kotlin',
                'description': 'Создание мобильных приложений для Android',
                'category_keywords': ['android'],
                'summary': 'Разработка нативных Android приложений с использованием Kotlin и Android Studio.',
            },
            {
                'name': 'AWS Cloud Computing',
                'description': 'Облачные технологии Amazon Web Services',
                'category_keywords': ['облачные'],
                'summary': 'Изучите основные сервисы AWS: EC2, S3, RDS, Lambda и другие.',
            },
            {
                'name': 'Flutter кроссплатформенная разработка',
                'description': 'Мобильные приложения на Flutter',
                'category_keywords': ['кроссплатформенная'],
                'summary': 'Создание приложений для iOS и Android с помощью Flutter и Dart.',
            }
        ]

        subjects = []
        for i in range(min(count, len(courses_data))):
            course_data = courses_data[i]
            
            # Находим подходящую категорию
            category = None
            for cat in categories:
                if any(keyword.lower() in cat.name.lower() for keyword in course_data['category_keywords']):
                    category = cat
                    break
            
            if not category:
                category = random.choice([cat for cat in categories if cat.parent is not None])

            subject = models['Subject'].objects.create(
                name=course_data['name'],
                description=course_data['description'],
                summary=course_data['summary'],
                teacher=random.choice(teachers),
                category=category,
                course_format=random.choice(formats),
                start_date=timezone.now().date() + timedelta(days=random.randint(1, 30)),
                end_date=timezone.now().date() + timedelta(days=random.randint(60, 120)),
                is_published=True,
                is_self_enrollment=random.choice([True, False]),
                completion_tracking=True,
                max_enrollment=random.randint(20, 100)
            )
            subjects.append(subject)

        return subjects

    def create_themes_and_lessons(self, subjects):
        """Создание тем и уроков для курсов"""
        models = self.get_models()
        for subject in subjects:
            # Создаем 3-5 тем для каждого курса
            themes_count = random.randint(3, 5)
            for theme_num in range(themes_count):
                theme = models['Theme'].objects.create(
                    name=f"Тема {theme_num + 1}: {self.get_theme_name(subject.name, theme_num)}",
                    description=f"Описание темы {theme_num + 1} курса {subject.name}",
                    subject=subject,
                    sort_order=theme_num
                )
                
                # Создаем 2-4 урока для каждой темы
                lessons_count = random.randint(2, 4)
                for lesson_num in range(lessons_count):
                    lesson_type = random.choice(['L', 'V', 'A', 'Q'])
                    lesson = models['Lesson'].objects.create(
                        name=f"Урок {lesson_num + 1}: {self.get_lesson_name(theme.name, lesson_num)}",
                        description=f"Подробное описание урока {lesson_num + 1}",
                        lessontype=lesson_type,
                        theme=theme,
                        sort_order=lesson_num,
                        is_visible=True
                    )

    def get_theme_name(self, course_name, theme_num):
        """Генерация названий тем в зависимости от курса"""
        theme_templates = {
            'Python': ['Основы синтаксиса', 'Структуры данных', 'ООП', 'Библиотеки', 'Проекты'],
            'React': ['Компоненты', 'Состояние и props', 'Хуки', 'Маршрутизация', 'Управление состоянием'],
            'Django': ['Модели', 'Представления', 'Шаблоны', 'Формы', 'REST API'],
            'JavaScript': ['Переменные и функции', 'DOM манипуляции', 'Асинхронность', 'ES6+ возможности', 'Отладка'],
            'Docker': ['Основы контейнеров', 'Dockerfile', 'Docker Compose', 'Volumes', 'Сети'],
            'SQL': ['SELECT запросы', 'Joins', 'Индексы', 'Транзакции', 'Процедуры'],
        }
        
        for key, themes in theme_templates.items():
            if key in course_name:
                return themes[theme_num % len(themes)]
        
        return f"Модуль {theme_num + 1}"

    def get_lesson_name(self, theme_name, lesson_num):
        """Генерация названий уроков"""
        lesson_templates = [
            'Введение и основы',
            'Практические примеры',
            'Углубленное изучение',
            'Задачи и упражнения',
            'Проектная работа'
        ]
        return lesson_templates[lesson_num % len(lesson_templates)]

    def create_tests_and_assignments(self, subjects):
        """Создание тестов и заданий"""
        models = self.get_models()
        for subject in subjects:
            # Создаем банк тестов
            test_bank = models['TestBank'].objects.create(
                name=f"Банк тестов - {subject.name}",
                description=f"Коллекция вопросов для курса {subject.name}",
                created_by=subject.teacher,
                subject=subject
            )

            # Получаем уроки для этого курса
            lessons = models['Lesson'].objects.filter(theme__subject=subject)
            
            if lessons.exists():
                # Создаем тесты для некоторых уроков
                selected_lessons = random.sample(list(lessons), min(2, len(lessons)))
                
                for lesson in selected_lessons:
                    test = models['Test'].objects.create(
                        name=f"Тест: {lesson.name}",
                        description=f"Проверочный тест по уроку {lesson.name}",
                        lesson=lesson,
                        test_bank=test_bank,
                        duration_minutes=random.randint(15, 45),
                        passing_score=random.randint(60, 80),
                        max_attempts=random.randint(1, 3),
                        randomize_questions=True,
                        available_from=timezone.now(),
                        available_until=timezone.now() + timedelta(days=30)
                    )

                    # Создаем вопросы для теста
                    questions_count = random.randint(3, 8)
                    for j in range(questions_count):
                        question = models['Question'].objects.create(
                            text=self.get_question_text(subject.name, j),
                            points=random.randint(1, 3),
                            type=random.choice(['S', 'M', 'TF']),
                            test=test,
                            test_bank=test_bank,
                            difficulty=random.choice(['easy', 'medium', 'hard'])
                        )

                        # Создаем варианты ответов
                        if question.type in ['S', 'M']:
                            answers_count = random.randint(3, 4)
                            correct_count = 1 if question.type == 'S' else random.randint(1, 2)
                            
                            for k in range(answers_count):
                                is_correct = k < correct_count
                                models['Answer'].objects.create(
                                    question=question,
                                    text=f"Вариант ответа {k + 1}",
                                    is_correct=is_correct
                                )
                        elif question.type == 'TF':
                            models['Answer'].objects.create(
                                question=question,
                                text="Истина",
                                is_correct=random.choice([True, False])
                            )
                            models['Answer'].objects.create(
                                question=question,
                                text="Ложь",
                                is_correct=True
                            )

            # Создаем задания для некоторых уроков  
            lessons = models['Lesson'].objects.filter(theme__subject=subject)
            if lessons.exists():
                selected_lessons = random.sample(list(lessons), min(2, len(lessons)))
                
                for i, lesson in enumerate(selected_lessons):
                    models['Assignment'].objects.create(
                        title=f"Практическое задание: {lesson.name}",
                        description=self.get_assignment_description(subject.name, i),
                        lesson=lesson,
                        deadline=timezone.now().date() + timedelta(days=random.randint(7, 21)),
                        max_grade=100,
                        submission_type=random.choice(['file', 'text', 'both']),
                        allow_late_submissions=random.choice([True, False])
                    )

    def get_question_text(self, course_name, question_num):
        """Генерация текста вопросов в зависимости от курса"""
        question_templates = {
            'Python': [
                'Какой тип данных используется для хранения последовательности символов?',
                'Что такое list comprehension в Python?',
                'Как создать виртуальное окружение в Python?',
                'Какая библиотека используется для работы с данными?',
                'Что такое декоратор в Python?'
            ],
            'React': [
                'Что такое JSX в React?',
                'Как передать данные от родительского компонента к дочернему?',
                'Что такое useState хук?',
                'Какая библиотека используется для маршрутизации в React?',
                'Что такое виртуальный DOM?'
            ],
            'Django': [
                'Что такое модель в Django?',
                'Как создать миграцию в Django?',
                'Что такое Django ORM?',
                'Как настроить URL маршрутизацию?',
                'Что такое middleware в Django?'
            ]
        }
        
        for key, questions in question_templates.items():
            if key in course_name:
                return questions[question_num % len(questions)]
        
        return f"Вопрос {question_num + 1} по курсу {course_name}"

    def get_assignment_description(self, course_name, assignment_num):
        """Генерация описаний заданий"""
        assignment_templates = {
            'Python': [
                'Создайте программу для анализа текстового файла',
                'Реализуйте простую игру на Python',
                'Создайте REST API используя Flask'
            ],
            'React': [
                'Создайте компонент для отображения списка задач',
                'Реализуйте форму с валидацией',
                'Создайте приложение-калькулятор'
            ],
            'Django': [
                'Создайте модель блога с комментариями',
                'Реализуйте систему аутентификации',
                'Создайте API для мобильного приложения'
            ]
        }
        
        for key, assignments in assignment_templates.items():
            if key in course_name:
                return assignments[assignment_num % len(assignments)]
        
        return f"Практическое задание {assignment_num + 1} по курсу {course_name}"

    def create_enrollments(self, subjects, students):
        """Создание записей студентов на курсы"""
        models = self.get_models()
        for student in students:
            # Каждый студент записывается на 2-4 случайных курса
            enrolled_courses = random.sample(subjects, random.randint(2, min(4, len(subjects))))
            
            for subject in enrolled_courses:
                models['Enrollment'].objects.create(
                    student=student,
                    subject=subject,
                    status=random.choice(['active', 'active', 'active', 'completed']),
                    progress_percentage=random.randint(0, 100) if random.choice([True, False]) else 0
                )

    def create_badges(self, subjects):
        """Создание значков для курсов"""
        models = self.get_models()
        badge_types = [
            ('course_completion', 'Завершение курса'),
            ('perfect_quiz', 'Отличный результат'),
            ('active_participant', 'Активный участник'),
            ('early_bird', 'Ранняя пасочка')
        ]

        for subject in subjects:
            # Создаем 1-2 значка для каждого курса
            badges_count = random.randint(1, 2)
            for i in range(badges_count):
                badge_type, type_name = random.choice(badge_types)
                models['Badge'].objects.create(
                    name=f"{type_name} - {subject.name}",
                    description=f"Получен за достижения в курсе {subject.name}",
                    badge_type=badge_type,
                    subject=subject,
                    criteria=f"Критерии получения значка для курса {subject.name}",
                    is_active=True
                ) 