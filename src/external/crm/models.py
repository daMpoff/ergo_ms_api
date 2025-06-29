from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Модели для управления проектами и задачами

class Project(models.Model):
    """Общий проект (не стратегический)"""
    PROJECT_STATUS_CHOICES = [
        ('planning', 'Планирование'),
        ('active', 'Активный'),
        ('on_hold', 'Приостановлен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Название проекта')
    description = models.TextField(blank=True, verbose_name='Описание')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects', verbose_name='Владелец проекта')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects', verbose_name='Менеджер проекта')
    team_members = models.ManyToManyField(User, through='ProjectMember', related_name='project_teams', verbose_name='Участники команды')
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='planning', verbose_name='Статус')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='Приоритет')
    start_date = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет проекта')  # Для календаря
    
    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    """Участник проекта"""
    ROLE_CHOICES = [
        ('member', 'Участник'),
        ('lead', 'Ведущий'),
        ('observer', 'Наблюдатель'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name='Роль')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата присоединения')
    
    class Meta:
        verbose_name = 'Участник проекта'
        verbose_name_plural = 'Участники проектов'
        unique_together = ['project', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.project.name}"


class Task(models.Model):
    """Задача"""
    TASK_STATUS_CHOICES = [
        ('todo', 'К выполнению'),
        ('in_progress', 'В работе'),
        ('review', 'На проверке'),
        ('done', 'Выполнено'),
        ('cancelled', 'Отменено'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    title = models.CharField(max_length=255, verbose_name='Название задачи')
    description = models.TextField(blank=True, verbose_name='Описание')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name='Проект')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks', verbose_name='Исполнитель')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks', verbose_name='Создатель')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='todo', verbose_name='Статус')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='Приоритет')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата начала')
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='Срок выполнения')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Оценка времени (часы)')
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Фактическое время (часы)')
    kanban_order = models.IntegerField(default=0, verbose_name='Порядок в канбан')
    
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['kanban_order', '-created_at']
    
    def __str__(self):
        return self.title


class TaskComment(models.Model):
    """Комментарий к задаче"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name='Задача')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_comments', verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Комментарий к задаче'
        verbose_name_plural = 'Комментарии к задачам'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Комментарий к {self.task.title}"


class TaskAttachment(models.Model):
    """Прикрепленный файл к задаче"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments', verbose_name='Задача')
    file = models.FileField(upload_to='task_attachments/', verbose_name='Файл')
    filename = models.CharField(max_length=255, verbose_name='Имя файла')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_attachments', verbose_name='Загрузил')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    
    class Meta:
        verbose_name = 'Прикрепленный файл'
        verbose_name_plural = 'Прикрепленные файлы'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.filename


class TimeLog(models.Model):
    """Учет времени по задаче"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_logs', verbose_name='Задача')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_logs', verbose_name='Пользователь')
    description = models.TextField(blank=True, verbose_name='Описание работы')
    hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Количество часов')
    date = models.DateField(verbose_name='Дата работы')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания записи')
    
    class Meta:
        verbose_name = 'Учет времени'
        verbose_name_plural = 'Учет времени'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.task.title} - {self.hours}ч"

# Создавайте свои модели здесь