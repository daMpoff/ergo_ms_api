from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Project(models.Model):
    """
    Модель проекта в CRM системе
    """
    name = models.CharField(max_length=255, verbose_name="Название проекта")
    dateofcreation = models.DateField(verbose_name="Дата создания", default=timezone.now)
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        db_column='creator_id',
        related_name='created_projects',
        verbose_name="Создатель проекта"
    )

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        db_table = 'crm_project'

    def __str__(self):
        return self.name

class Section(models.Model):
    """
    Модель секции/раздела в проекте
    """
    name = models.CharField(max_length=255, verbose_name="Название секции")
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_column='project_id',
        related_name='sections',
        verbose_name="Проект"
    )

    class Meta:
        verbose_name = "Секция"
        verbose_name_plural = "Секции"
        db_table = 'crm_section'
        unique_together = ('name', 'project')

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class Task(models.Model):
    """
    Модель задачи в CRM системе
    """
    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
    ]

    text = models.CharField(max_length=255, verbose_name="Текст задачи")
    isdone = models.BooleanField(default=False, verbose_name="Выполнена")
    description = models.TextField(blank=True, verbose_name="Описание")
    dateofcreation = models.DateField(verbose_name="Дата создания", default=timezone.now)
    deadline = models.DateField(verbose_name="Срок выполнения", null=True, blank=True)
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=2,
        verbose_name="Приоритет"
    )
    parenttask = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='parenttask_id',
        related_name='subtasks',
        verbose_name="Родительская задача"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='section_id',
        related_name='tasks',
        verbose_name="Секция"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='tasks',
        verbose_name="Пользователь"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата завершения"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_column='project_id',
        related_name='tasks',
        verbose_name="Проект"
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        db_table = 'crm_task'
        ordering = ['-priority', 'deadline']

    def __str__(self):
        return f"{self.text} ({self.get_priority_display()})"

    def save(self, *args, **kwargs):
        if self.isdone and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.isdone and self.completed_at:
            self.completed_at = None
        super().save(*args, **kwargs)

class Calendar (models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(default='')
    time = models.DateTimeField(default= timezone.now)

class User_Project(models.Model):
    isnew = models.BooleanField(default=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'crm_user_project'