from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectStatus(models.Model):
    """Статусы проектов"""
    name = models.CharField(max_length=100, verbose_name='Название статуса')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код статуса')
    description = models.TextField(blank=True, verbose_name='Описание')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет')
    order = models.IntegerField(default=0, verbose_name='Порядок сортировки')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_default = models.BooleanField(default=False, verbose_name='По умолчанию')
    is_final = models.BooleanField(default=False, verbose_name='Финальный статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        app_label = 'crm'
        verbose_name = 'Статус проекта'
        verbose_name_plural = 'Статусы проектов'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ProjectPriority(models.Model):
    """Приоритеты проектов"""
    name = models.CharField(max_length=100, verbose_name='Название приоритета')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код приоритета')
    description = models.TextField(blank=True, verbose_name='Описание')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет')
    level = models.IntegerField(default=1, verbose_name='Уровень приоритета')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_default = models.BooleanField(default=False, verbose_name='По умолчанию')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        app_label = 'crm'
        verbose_name = 'Приоритет проекта'
        verbose_name_plural = 'Приоритеты проектов'
        ordering = ['level', 'name']
    
    def __str__(self):
        return self.name


class TaskStatus(models.Model):
    """Статусы задач"""
    name = models.CharField(max_length=100, verbose_name='Название статуса')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код статуса')
    description = models.TextField(blank=True, verbose_name='Описание')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет')
    order = models.IntegerField(default=0, verbose_name='Порядок сортировки')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_default = models.BooleanField(default=False, verbose_name='По умолчанию')
    is_final = models.BooleanField(default=False, verbose_name='Финальный статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        app_label = 'crm'
        verbose_name = 'Статус задачи'
        verbose_name_plural = 'Статусы задач'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class TaskPriority(models.Model):
    """Приоритеты задач"""
    name = models.CharField(max_length=100, verbose_name='Название приоритета')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код приоритета')
    description = models.TextField(blank=True, verbose_name='Описание')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет')
    level = models.IntegerField(default=1, verbose_name='Уровень приоритета')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_default = models.BooleanField(default=False, verbose_name='По умолчанию')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        app_label = 'crm'
        verbose_name = 'Приоритет задачи'
        verbose_name_plural = 'Приоритеты задач'
        ordering = ['level', 'name']
    
    def __str__(self):
        return self.name

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
    
    # Новые поля с внешними ключами
    status_ref = models.ForeignKey(ProjectStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects', verbose_name='Статус (новый)')
    priority_ref = models.ForeignKey(ProjectPriority, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects', verbose_name='Приоритет (новый)')
    
    # Старые поля для обратной совместимости
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='planning', verbose_name='Статус')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='Приоритет')
    
    start_date = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет проекта')  # Для календаря
    
    class Meta:
        app_label = 'crm'
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def current_status(self):
        """Получить текущий статус (приоритет новому полю)"""
        return self.status_ref.code if self.status_ref else self.status
    
    @property
    def current_priority(self):
        """Получить текущий приоритет (приоритет новому полю)"""
        return self.priority_ref.code if self.priority_ref else self.priority
    
    @property
    def status_display(self):
        """Получить отображаемое название статуса"""
        return self.status_ref.name if self.status_ref else dict(self.PROJECT_STATUS_CHOICES).get(self.status, self.status)
    
    @property
    def priority_display(self):
        """Получить отображаемое название приоритета"""
        return self.priority_ref.name if self.priority_ref else dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)


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
        app_label = 'crm'
        verbose_name = 'Участник проекта'
        verbose_name_plural = 'Участники проектов'
        unique_together = ['project', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.project.name}"


class Task(models.Model):
    """Задача"""
    # Обратная совместимость - старые choices остаются как fallback
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
    
    # Новые поля с внешними ключами
    status_ref = models.ForeignKey(TaskStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', verbose_name='Статус (новый)')
    priority_ref = models.ForeignKey(TaskPriority, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', verbose_name='Приоритет (новый)')
    
    # Старые поля для обратной совместимости
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
        app_label = 'crm'
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['kanban_order', '-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def current_status(self):
        """Получить текущий статус (приоритет новому полю)"""
        return self.status_ref.code if self.status_ref else self.status
    
    @property
    def current_priority(self):
        """Получить текущий приоритет (приоритет новому полю)"""
        return self.priority_ref.code if self.priority_ref else self.priority
    
    @property
    def status_display(self):
        """Получить отображаемое название статуса"""
        return self.status_ref.name if self.status_ref else dict(self.TASK_STATUS_CHOICES).get(self.status, self.status)
    
    @property
    def priority_display(self):
        """Получить отображаемое название приоритета"""
        return self.priority_ref.name if self.priority_ref else dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)


class TaskComment(models.Model):
    """Комментарий к задаче"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name='Задача')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_comments', verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        app_label = 'crm'
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
        app_label = 'crm'
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
        app_label = 'crm'
        verbose_name = 'Учет времени'
        verbose_name_plural = 'Учет времени'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.task.title} - {self.hours}ч"

# Создавайте свои модели здесь