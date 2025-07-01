from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


# Роли пользователей в системе
class UserRole(models.Model):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
        ('moderator', 'Модератор'),
        ('guest', 'Гость'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'lms'
        unique_together = ['user', 'role']

# Профиль пользователя с расширенной информацией
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='ru')
    email_notifications = models.BooleanField(default=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'lms'

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    department = models.CharField(max_length=200, blank=True)
    academic_degree = models.CharField(max_length=100, blank=True)
    office_hours = models.TextField(blank=True)

    class Meta:
        app_label = 'lms'
    
class StudentGroup(models.Model):
    name = models.CharField(max_length=255, default='')
    curator = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=200, blank=True)
    year_of_study = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'lms'

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    enrollment_date = models.DateField(default=timezone.now)

    class Meta:
        app_label = 'lms'

# Категории курсов
class CourseCategory(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    sort_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'lms'
        verbose_name_plural = "Course Categories"
        ordering = ['sort_order', 'name']

# Форматы курсов
class CourseFormat(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'lms'
        verbose_name_plural = "Course Formats"
        ordering = ['name']

# Расширенная модель курса (предмета)
class Subject(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    
    # Новые поля в стиле Moodle
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    course_format = models.ForeignKey(CourseFormat, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    enrollment_key = models.CharField(max_length=50, blank=True)
    max_enrollment = models.IntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)
    course_image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    is_self_enrollment = models.BooleanField(default=False)
    completion_tracking = models.BooleanField(default=False)
    guest_access = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

    class Meta:
        app_label = 'lms'
        ordering = ['-creationdate']

# Записи на курс
class Enrollment(models.Model):
    ENROLLMENT_STATUS = [
        ('active', 'Активен'),
        ('suspended', 'Приостановлен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS, default='active')
    completion_date = models.DateTimeField(null=True, blank=True)
    progress_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    class Meta:
        app_label = 'lms'
        unique_together = ['student', 'subject']

class Grade(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, default=0)
    related = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    grade = models.IntegerField(default=0)
    
    # Дополнительные поля для оценивания
    grader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_grades', null=True, blank=True)
    feedback = models.TextField(blank=True)
    grade_type = models.CharField(max_length=50, default='manual')  # manual, automatic, peer

    class Meta:
        app_label = 'lms'

class Theme(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, default=0)
    
    # Дополнительные поля
    sort_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    completion_required = models.BooleanField(default=False)

    class Meta:
        app_label = 'lms'

class Lesson(models.Model):
    class LessonType(models.TextChoices):
        video = 'V'
        conference = 'C'
        lecture = 'L'
        assignment = 'A'
        quiz = 'Q'
        forum = 'F'
        file = 'FILE'
        url = 'URL'
        
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    lessontype = models.CharField(max_length=40, choices=LessonType.choices, default=LessonType.lecture)
    content = models.BinaryField(default=b'\x08')
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE)
    
    # Новые поля
    availability_start = models.DateTimeField(null=True, blank=True)
    availability_end = models.DateTimeField(null=True, blank=True)
    completion_required = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        app_label = 'lms'

# Ресурсы (файлы) - могут принадлежать курсу, теме или уроку
class Resource(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/')
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Гибкая привязка - ресурс может принадлежать курсу, теме или уроку
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='resources')
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True, related_name='resources')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='resources')
    
    def __str__(self):
        return self.name

    class Meta:
        app_label = 'lms'
        ordering = ['sort_order', 'name']

# Файлы и ресурсы курса (оставляем для обратной совместимости)
class CourseFile(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='files')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='course_files/')
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        app_label = 'lms'

# Форумы
class Forum(models.Model):
    FORUM_TYPES = [
        ('general', 'Общий форум'),
        ('q_and_a', 'Вопросы и ответы'),
        ('single', 'Одна дискуссия'),
        ('each_person', 'Каждый участник создает одну тему'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    forum_type = models.CharField(max_length=20, choices=FORUM_TYPES, default='general')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_locked = models.BooleanField(default=False)
    allow_subscriptions = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Гибкая привязка - форум может принадлежать курсу, теме или уроку
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='forums')
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True, related_name='forums')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='forums')
    
    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'lms'

# Дискуссии форума
class ForumDiscussion(models.Model):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name='discussions')
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_post_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    posts_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'lms'

# Посты в дискуссиях
class ForumPost(models.Model):
    discussion = models.ForeignKey(ForumDiscussion, on_delete=models.CASCADE, related_name='posts')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    attachments = models.ManyToManyField(CourseFile, blank=True)
    
    def __str__(self):
        return f"Post by {self.author.username} in {self.discussion.name}"
    
    class Meta:
        app_label = 'lms'


# Календарь событий
class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ('assignment', 'Задание'),
        ('quiz', 'Тест'),
        ('lesson', 'Урок'),
        ('exam', 'Экзамен'),
        ('deadline', 'Крайний срок'),
        ('other', 'Другое'),
    ]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        app_label = 'lms'

# Значки и достижения
class Badge(models.Model):
    BADGE_TYPES = [
        ('course_completion', 'Завершение курса'),
        ('perfect_quiz', 'Отличный результат теста'),
        ('active_participant', 'Активный участник'),
        ('early_bird', 'Ранняя птичка'),
        ('helpful', 'Помощник'),
        ('custom', 'Настраиваемый'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    badge_type = models.CharField(max_length=30, choices=BADGE_TYPES, default='custom')
    image = models.ImageField(upload_to='badges/', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='badges')
    criteria = models.TextField()  # Критерии получения значка
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'lms'

# Выданные значки
class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)
    awarded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='awarded_badges', null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'badge']

    class Meta:
        app_label = 'lms'

# Оставшиеся модели остаются без изменений
class TestBank(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='test_banks')

    def __str__(self):
        return self.name
    
    class Meta:
        app_label = 'lms'

class Test(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    timelimit = models.IntegerField(default=0)
    
    # Гибкая привязка - тест может принадлежать курсу, теме или уроку
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='tests')
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True, related_name='tests')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='tests')
    
    class TestType(models.TextChoices):
        close = 'C'
        game = 'G'
        open = 'O'
        
    type = models.CharField(max_length=100, choices=TestType, default=TestType.close)   
    title = models.CharField(max_length=255, default='')
    test_bank = models.ForeignKey(TestBank, on_delete=models.CASCADE, related_name='tests', null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    passing_score = models.IntegerField(default=70)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Новые поля для тестов
    max_attempts = models.IntegerField(default=1)
    show_correct_answers = models.BooleanField(default=False)
    randomize_questions = models.BooleanField(default=False)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['sort_order', 'creationdate']
        app_label = 'lms'

class Question(models.Model):
    text = models.TextField(default='')
    points = models.IntegerField(default=0)
    lastupdate = models.DateTimeField(default=timezone.now)
    correctanswer = models.TextField(default='')
    
    class QuestionType(models.TextChoices):
        single = 'S'
        open = 'O'
        multiple = 'M'
        true_false = 'TF'
        matching = 'MATCH'
        
    type = models.CharField(max_length=100, choices=QuestionType, default=QuestionType.single)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    test_bank = models.ForeignKey(TestBank, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    
    # Дополнительные поля
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=[('easy', 'Легкий'), ('medium', 'Средний'), ('hard', 'Сложный')], default='medium')

    class Meta:
        app_label = 'lms'

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.text[:50]}..."

    class Meta:
        app_label = 'lms'

class TestAttempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    is_passed = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=20, default='in_progress')
    attempt_number = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.student.username} - {self.test.title}"

    def calculate_score(self):
        """Calculate the score as a percentage"""
        total_points = 0
        earned_points = 0
        
        for answer in self.answers.all():
            question = answer.question
            total_points += question.points
            
            if answer.is_correct:
                earned_points += question.points
        
        if total_points > 0:
            return (earned_points / total_points) * 100
        return 0

    class Meta:
        app_label = 'lms'

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer for {self.question.text[:50]}..."

    def check_correctness(self):
        """Check if the answer is correct"""
        if self.question.type == 'S':  # Single choice
            correct_answer = self.question.answers.filter(is_correct=True).first()
            selected_answer = self.selections.first()
            self.is_correct = selected_answer and selected_answer.answer == correct_answer
        elif self.question.type == 'M':  # Multiple choice
            correct_answers = set(self.question.answers.filter(is_correct=True))
            selected_answers = set(selection.answer for selection in self.selections.all())
            self.is_correct = correct_answers == selected_answers
        elif self.question.type == 'O':  # Open answer
            self.is_correct = self.text_answer.strip().lower() == self.question.correctanswer.strip().lower()
        self.save()

    class Meta:
        app_label = 'lms'

class StudentAnswerSelection(models.Model):
    student_answer = models.ForeignKey(StudentAnswer, on_delete=models.CASCADE, related_name='selections')
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Selection for {self.answer.text[:50]}..."

    class Meta:
        app_label = 'lms'

# UserAnswer модель удалена, используем StudentAnswer вместо неё

class Assignment(models.Model):
    title = models.CharField(max_length=255, default='')
    description = models.TextField(default='')
    deadline = models.DateField(null=True, blank=True)
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    
    # Гибкая привязка - задание может принадлежать курсу, теме или уроку
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='assignments')
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True, related_name='assignments')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='assignments')
    
    # Дополнительные поля
    max_grade = models.IntegerField(default=100)
    allow_late_submissions = models.BooleanField(default=False)
    submission_type = models.CharField(max_length=50, choices=[
        ('file', 'Файл'),
        ('text', 'Текст'),
        ('both', 'Файл и текст')
    ], default='file')
    max_file_size = models.IntegerField(default=10485760)  # 10MB in bytes
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'deadline']
        app_label = 'lms'

class SubmittedAssignment(models.Model):
    submittedassignment = models.BinaryField(default=b'\x08')
    comment = models.TextField(default='')
    grade = models.IntegerField(default=0)
    dateofsubmit = models.DateField(default=timezone.now)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    
    # Дополнительные поля
    submission_text = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_assignments')
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'lms'

# Система уведомлений
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('assignment_due', 'Крайний срок задания'),
        ('grade_posted', 'Выставлена оценка'),
        ('new_forum_post', 'Новый пост на форуме'),
        ('course_update', 'Обновление курса'),
        ('message', 'Личное сообщение'),
        ('badge_awarded', 'Получен значок'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    class Meta:
        app_label = 'lms'

# Личные сообщения
class PrivateMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=255)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.subject} - {self.sender} to {self.recipient}"
    
    class Meta:
        app_label = 'lms'

# Унифицированная модель для элементов урока (тесты, задания, ресурсы)
class LessonItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('test', 'Тест'),
        ('assignment', 'Задание'),
        ('resource', 'Ресурс'),
    ]
    
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='lesson_items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    sort_order = models.IntegerField(default=0)
    
    # Гибкие связи - только одна из них должна быть заполнена
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True, related_name='lesson_items')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True, related_name='lesson_items')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, null=True, blank=True, related_name='lesson_items')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'created_at']
        app_label = 'lms'
        unique_together = [
            ['lesson', 'test'],
            ['lesson', 'assignment'], 
            ['lesson', 'resource']
        ]
    
    def clean(self):
        """Валидация: должен быть заполнен ровно один из типов элементов"""
        filled_fields = sum([
            bool(self.test),
            bool(self.assignment),
            bool(self.resource)
        ])
        
        if filled_fields != 1:
            raise ValidationError("Должен быть заполнен ровно один тип элемента")
        
        # Автоматически устанавливаем item_type на основе заполненного поля
        if self.test:
            self.item_type = 'test'
        elif self.assignment:
            self.item_type = 'assignment'
        elif self.resource:
            self.item_type = 'resource'
    
    def get_content_object(self):
        """Возвращает связанный объект контента"""
        if self.test:
            return self.test
        elif self.assignment:
            return self.assignment
        elif self.resource:
            return self.resource
        return None
    
    def get_display_name(self):
        """Возвращает отображаемое имя элемента"""
        content = self.get_content_object()
        if not content:
            return f"Элемент урока #{self.id}"
        
        if hasattr(content, 'title') and content.title:
            return content.title
        elif hasattr(content, 'name') and content.name:
            return content.name
        return f"{self.get_item_type_display()} #{content.id}"
    
    def __str__(self):
        return f"{self.lesson.name} - {self.get_display_name()}"
