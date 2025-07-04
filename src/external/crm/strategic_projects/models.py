from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class DevelopmentProgram(models.Model):
    """Программа развития (ПрРаз)"""
    name = models.CharField(max_length=255, verbose_name='Название программы')
    year = models.IntegerField(verbose_name='Год программы')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    class Meta:
        verbose_name = 'Программа развития'
        verbose_name_plural = 'Программы развития'
        ordering = ['-year', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.year})"


class ProgramTopic(models.Model):
    """Тема/Направление программы развития"""
    TOPIC_STATUS_CHOICES = [
        ('free', 'Свободно'),
        ('reserved', 'Занято'),
    ]
    
    program = models.ForeignKey(DevelopmentProgram, on_delete=models.CASCADE, related_name='topics')
    direction_code = models.CharField(max_length=50, verbose_name='Код направления')
    topic_number = models.CharField(max_length=50, verbose_name='Номер темы')
    name = models.CharField(max_length=500, verbose_name='Наименование темы')
    description = models.TextField(blank=True, verbose_name='Описание')
    planned_start_date = models.DateField(verbose_name='Плановая дата начала')
    planned_end_date = models.DateField(verbose_name='Плановая дата окончания')
    expected_results = models.JSONField(default=list, verbose_name='Ожидаемые результаты')
    status = models.CharField(max_length=20, choices=TOPIC_STATUS_CHOICES, default='free', verbose_name='Статус')
    project = models.OneToOneField('StrategicProject', on_delete=models.SET_NULL, null=True, blank=True, related_name='topic_link')
    
    class Meta:
        verbose_name = 'Тема программы развития'
        verbose_name_plural = 'Темы программы развития'
        unique_together = ['program', 'direction_code', 'topic_number']
    
    def __str__(self):
        return f"{self.direction_code}-{self.topic_number}: {self.name}"


class StrategicProject(models.Model):
    """Стратегический проект"""
    PROJECT_STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('on_approval', 'На утверждении'),
        ('rejected', 'Отклонен'),
        ('approved', 'Утвержден'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершен'),
        ('archived', 'Архив'),
    ]
    
    topic = models.ForeignKey(ProgramTopic, on_delete=models.PROTECT, related_name='projects')
    name = models.CharField(max_length=500, verbose_name='Название проекта')
    code = models.CharField(max_length=100, unique=True, verbose_name='Код проекта')
    leader = models.ForeignKey(User, on_delete=models.PROTECT, related_name='strategic_led_projects', verbose_name='Руководитель проекта')
    curator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='strategic_curated_projects', verbose_name='Куратор проекта')
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='strategic_customer_projects', verbose_name='Заказчик проекта')
    goal = models.TextField(verbose_name='Цель проекта')
    tasks = models.TextField(verbose_name='Задачи проекта')
    planned_results = models.JSONField(default=list, verbose_name='Планируемые результаты')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    planned_start_date = models.DateField(verbose_name='Плановая дата начала')
    planned_end_date = models.DateField(verbose_name='Плановая дата окончания')
    actual_start_date = models.DateField(null=True, blank=True, verbose_name='Фактическая дата начала')
    actual_end_date = models.DateField(null=True, blank=True, verbose_name='Фактическая дата окончания')
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='draft', verbose_name='Статус проекта')
    requires_budget = models.BooleanField(default=False, verbose_name='Требуется бюджет')
    total_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Общий бюджет')
    rejection_comment = models.TextField(blank=True, verbose_name='Комментарий при отклонении')
    
    class Meta:
        verbose_name = 'Стратегический проект'
        verbose_name_plural = 'Стратегические проекты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code}: {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.code and self.topic:
            # Автогенерация кода проекта
            year = timezone.now().year
            initials = ''.join([name[0].upper() for name in self.leader.get_full_name().split() if name])
            self.code = f"{self.topic.direction_code}-{self.topic.topic_number}-{year}-{initials}"
        super().save(*args, **kwargs)


class ProjectStage(models.Model):
    """Этап проекта"""
    STAGE_STATUS_CHOICES = [
        ('planned', 'Запланирован'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершен'),
        ('delayed', 'Просрочен'),
    ]
    
    project = models.ForeignKey(StrategicProject, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=255, verbose_name='Наименование этапа')
    description = models.TextField(blank=True, verbose_name='Описание')
    planned_start_date = models.DateField(verbose_name='Плановая дата начала')
    planned_end_date = models.DateField(verbose_name='Плановая дата окончания')
    actual_start_date = models.DateField(null=True, blank=True, verbose_name='Фактическая дата начала')
    actual_end_date = models.DateField(null=True, blank=True, verbose_name='Фактическая дата окончания')
    status = models.CharField(max_length=20, choices=STAGE_STATUS_CHOICES, default='planned', verbose_name='Статус этапа')
    expected_results = models.JSONField(default=list, verbose_name='Ожидаемые результаты')
    target_indicators = models.JSONField(default=list, verbose_name='Целевые показатели')
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Бюджет этапа')
    order_number = models.IntegerField(verbose_name='Порядковый номер')
    
    class Meta:
        verbose_name = 'Этап проекта'
        verbose_name_plural = 'Этапы проекта'
        ordering = ['project', 'order_number']
        unique_together = ['project', 'order_number']
    
    def __str__(self):
        return f"{self.project.code} - Этап {self.order_number}: {self.name}"


class StageExecutor(models.Model):
    """Исполнитель этапа"""
    EXECUTOR_ROLE_CHOICES = [
        ('main', 'Основной исполнитель'),
        ('assistant', 'Помощник'),
        ('consultant', 'Консультант'),
    ]
    
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name='executors')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategic_stage_executions')
    role = models.CharField(max_length=20, choices=EXECUTOR_ROLE_CHOICES, default='main', verbose_name='Роль в этапе')
    assigned_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата назначения')
    
    class Meta:
        verbose_name = 'Исполнитель этапа'
        verbose_name_plural = 'Исполнители этапов'
        unique_together = ['stage', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.stage.name}"


class ProjectReport(models.Model):
    """Отчет по проекту"""
    REPORT_TYPE_CHOICES = [
        ('monthly', 'Месячный'),
        ('intermediate', 'Промежуточный'),
        ('final', 'Итоговый'),
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('on_approval', 'На согласовании'),
        ('approved', 'Согласован'),
        ('rejected', 'Отклонен'),
    ]
    
    project = models.ForeignKey(StrategicProject, on_delete=models.CASCADE, related_name='reports')
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name='Тип отчета')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    content = models.TextField(verbose_name='Содержание отчета')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='draft', verbose_name='Статус согласования')
    comments = models.TextField(blank=True, verbose_name='Комментарии')
    attachments = models.JSONField(default=list, verbose_name='Прикрепленные файлы')
    
    class Meta:
        verbose_name = 'Отчет по проекту'
        verbose_name_plural = 'Отчеты по проектам'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_report_type_display()} отчет - {self.project.code}"


class StageResult(models.Model):
    """Результат этапа"""
    RESULT_TYPE_CHOICES = [
        ('document', 'Документ'),
        ('product', 'Продукт'),
        ('service', 'Услуга'),
        ('other', 'Прочее'),
    ]
    
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name='results')
    description = models.TextField(verbose_name='Описание результата')
    result_type = models.CharField(max_length=20, choices=RESULT_TYPE_CHOICES, verbose_name='Тип результата')
    files = models.JSONField(default=list, verbose_name='Файлы/ссылки')
    added_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    class Meta:
        verbose_name = 'Результат этапа'
        verbose_name_plural = 'Результаты этапов'
        ordering = ['-added_date']
    
    def __str__(self):
        return f"{self.stage.name} - {self.get_result_type_display()}"


class ProjectHistory(models.Model):
    """История изменений проекта"""
    project = models.ForeignKey(StrategicProject, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='strategic_project_histories')
    action = models.CharField(max_length=100, verbose_name='Действие')
    description = models.TextField(verbose_name='Описание изменения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')
    old_value = models.JSONField(null=True, blank=True, verbose_name='Старое значение')
    new_value = models.JSONField(null=True, blank=True, verbose_name='Новое значение')
    
    class Meta:
        verbose_name = 'История изменений'
        verbose_name_plural = 'История изменений'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.code} - {self.action} - {self.created_at}"


class UserProjectRole(models.Model):
    """Роли пользователей в модуле стратегических проектов"""
    ROLE_CHOICES = [
        ('admin', 'Администратор СтрПр'),
        ('curator_sp', 'Куратор СтрПр'),
        ('expert_group', 'Экспертная группа'),
        ('expert_lead', 'Руководитель ЭГ'),
        ('project_lead', 'Руководитель проекта'),
        ('customer', 'Заказчик проекта'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategic_project_roles')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Роль')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата назначения')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_roles')
    
    class Meta:
        verbose_name = 'Роль пользователя в СтрПр'
        verbose_name_plural = 'Роли пользователей в СтрПр'
        unique_together = ['user', 'role']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class EmployeeWorkload(models.Model):
    """Загруженность сотрудников в проектах"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategic_workload')
    project = models.ForeignKey(StrategicProject, on_delete=models.CASCADE, related_name='employee_workload')
    role_in_project = models.CharField(max_length=50, verbose_name='Роль в проекте')
    workload_percentage = models.IntegerField(default=0, verbose_name='Процент загрузки')
    start_date = models.DateField(verbose_name='Дата начала участия')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания участия')
    
    class Meta:
        verbose_name = 'Загруженность сотрудника'
        verbose_name_plural = 'Загруженность сотрудников'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.project.code} ({self.workload_percentage}%)"


class ProjectNotification(models.Model):
    """Модель уведомлений по стратегическим проектам"""
    
    NOTIFICATION_TYPES = [
        ('status_change', 'Изменение статуса'),
        ('approval_required', 'Требуется утверждение'),
        ('project_approved', 'Проект утвержден'),
        ('project_rejected', 'Проект отклонен'),
        ('deadline_approaching', 'Приближается срок'),
        ('task_assigned', 'Назначена задача'),
        ('stage_completed', 'Этап завершен'),
        ('comment_added', 'Добавлен комментарий'),
        ('project_started', 'Проект запущен'),
        ('project_completed', 'Проект завершен'),
    ]
    
    project = models.ForeignKey(
        StrategicProject,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Проект'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_notifications',
        verbose_name='Получатель'
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        verbose_name='Тип уведомления'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Заголовок'
    )
    message = models.TextField(
        verbose_name='Сообщение'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата прочтения'
    )
    
    class Meta:
        verbose_name = 'Уведомление проекта'
        verbose_name_plural = 'Уведомления проектов'
        ordering = ['-created_at']
        
    def __str__(self):
        return f'{self.title} - {self.recipient.get_full_name()}'
    
    def mark_as_read(self):
        """Отметить уведомление как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @classmethod
    def create_notification(cls, project, recipient, notification_type, title, message):
        """Создать уведомление"""
        return cls.objects.create(
            project=project,
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message
        )
    
    @classmethod
    def notify_status_change(cls, project, old_status, new_status):
        """Уведомление об изменении статуса проекта"""
        recipients = []
        
        # Уведомляем руководителя проекта
        if project.leader:
            recipients.append(project.leader)
        
        # Уведомляем куратора
        if project.curator:
            recipients.append(project.curator)
        
        # Уведомляем заказчика
        if project.customer:
            recipients.append(project.customer)
        
        # Если проект отправлен на утверждение, уведомляем экспертную группу
        if new_status == 'on_approval':
            expert_roles = UserProjectRole.objects.filter(
                role__in=['expert_group', 'expert_lead']
            )
            for role in expert_roles:
                recipients.append(role.user)
        
        status_labels = {
            'draft': 'Черновик',
            'on_approval': 'На утверждении',
            'rejected': 'Отклонен',
            'approved': 'Утвержден',
            'in_progress': 'В работе',
            'completed': 'Завершен',
            'archived': 'Архив'
        }
        
        for recipient in set(recipients):
            cls.create_notification(
                project=project,
                recipient=recipient,
                notification_type='status_change',
                title=f'Изменение статуса проекта "{project.name}"',
                message=f'Статус проекта изменен с "{status_labels.get(old_status, old_status)}" на "{status_labels.get(new_status, new_status)}"'
            )
    
    @classmethod
    def notify_deadline_approaching(cls, project, days_remaining):
        """Уведомление о приближающемся сроке"""
        recipients = [project.leader]
        if project.curator:
            recipients.append(project.curator)
        
        for recipient in set(recipients):
            cls.create_notification(
                project=project,
                recipient=recipient,
                notification_type='deadline_approaching',
                title=f'Приближается срок завершения проекта "{project.name}"',
                message=f'До завершения проекта осталось {days_remaining} дней. Плановая дата окончания: {project.planned_end_date}'
            ) 