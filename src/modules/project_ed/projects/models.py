from django.db import models
from django.conf import settings


class ProjectTask(models.Model):
    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='tasks', verbose_name='Проект')
    description = models.TextField('Задача')
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Задача проекта'
        verbose_name_plural = 'Задачи проекта'
        ordering = ['order', 'id']


class ProjectExecutor(models.Model):
    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='executors', verbose_name='Проект')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='executed_projects', verbose_name='Пользователь')
    role = models.CharField('Роль в проекте', max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Исполнитель проекта'
        verbose_name_plural = 'Исполнители проекта'
        unique_together = [('project', 'user')]


class ProjectPlannedResult(models.Model):
    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='planned_results', verbose_name='Проект')
    description = models.TextField('Планируемый результат')
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Планируемый результат'
        verbose_name_plural = 'Планируемые результаты'
        ordering = ['order', 'id']


class ProjectTargetIndicator(models.Model):
    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='target_indicators_rel', verbose_name='Проект')
    source_indicator = models.ForeignKey('project_ed.TargetIndicator', on_delete=models.SET_NULL, null=True, blank=True, related_name='project_target_indicators', verbose_name='Исходный целевой показатель')
    name = models.CharField('Наименование', max_length=255)
    unit = models.CharField('Единица измерения', max_length=50, blank=True, default='')
    baseline = models.DecimalField('Базовое значение', max_digits=14, decimal_places=2, null=True, blank=True)
    planned = models.DecimalField('Планируемое значение', max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Целевой показатель проекта'
        verbose_name_plural = 'Целевые показатели проекта'
        ordering = ['name', 'id']

    @property
    def is_manual(self):
        return self.source_indicator is None

    @property
    def display_name(self):
        return self.name or (self.source_indicator.name if self.source_indicator else '')

    @property
    def display_unit(self):
        return self.unit or (self.source_indicator.unit if self.source_indicator else '')


class ProjectStage(models.Model):
    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='stages', verbose_name='Проект')
    name = models.CharField('Наименование этапа', max_length=255)
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    planned_results = models.TextField('Планируемые результаты', blank=True, default='')
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Этап проекта'
        verbose_name_plural = 'Этапы проекта'
        ordering = ['order', 'start_date', 'id']


class ProjectBudgetItem(models.Model):
    STAGE_COST_ARTICLE_MAX_LEN = 255
    FUNDING_SOURCE_MAX_LEN = 255

    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='budget_items', verbose_name='Проект')
    stage = models.ForeignKey(ProjectStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_items', verbose_name='Этап')
    cost_article = models.CharField('Статья расходов', max_length=STAGE_COST_ARTICLE_MAX_LEN)
    funding_source = models.CharField('Источник финансирования', max_length=FUNDING_SOURCE_MAX_LEN)
    amount = models.DecimalField('Сумма', max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'Бюджет: позиция'
        verbose_name_plural = 'Бюджет: позиции'
        ordering = ['project_id', 'stage_id', 'id']


class ProjectBudgetTotal(models.Model):
    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='budget_totals', verbose_name='Проект')
    total_with_insurance = models.DecimalField('Итого с страховкой', max_digits=14, decimal_places=2, default=0)
    salary_off_budget = models.DecimalField('Зарплата (внебюджет)', max_digits=14, decimal_places=2, default=0)
    salary_budget = models.DecimalField('Зарплата (бюджет)', max_digits=14, decimal_places=2, default=0)
    other_off_budget = models.DecimalField('Другие расходы (внебюджет)', max_digits=14, decimal_places=2, default=0)
    other_budget = models.DecimalField('Другие расходы (бюджет)', max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Бюджет: итоги'
        verbose_name_plural = 'Бюджет: итоги'


class ProjectVersion(models.Model):
    """Снимок версии проекта для истории изменений.

    Хранит денормализованный JSON состояния проекта (включая связанные сущности),
    чтобы быстро просматривать прошлые версии без сложной реконструкции из множества таблиц.
    """

    project = models.ForeignKey('project_ed.Project', on_delete=models.CASCADE, related_name='versions', verbose_name='Проект')
    version_number = models.PositiveIntegerField('Номер версии')
    title = models.CharField('Заголовок/метка версии', max_length=255, blank=True, default='')
    payload = models.JSONField('Снимок данных проекта')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_ed_created_versions', verbose_name='Кем создано')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Версия проекта'
        verbose_name_plural = 'Версии проекта'
        ordering = ['-created_at']
        unique_together = [('project', 'version_number')]

    def __str__(self):
        return f'Project #{self.project_id} v{self.version_number}'


# --- Роли в рамках проекта ---
class ProjectRole(models.Model):
    """Справочник ролей в рамках ProjectEd-проекта.

    Примеры: 'Руководитель', 'Куратор', 'Заказчик', 'Исполнитель'.
    """
    name = models.CharField('Роль в проекте', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Роль проекта (справочник)'
        verbose_name_plural = 'Роли проекта (справочник)'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class ProjectUserRole(models.Model):
    """Связь пользователь ↔ проект ↔ роль (многие ко многим с атрибутом роль)."""

    project = models.ForeignKey(
        'project_ed.Project',
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='Проект',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_ed_roles',
        verbose_name='Пользователь',
    )
    role = models.ForeignKey(
        ProjectRole,
        on_delete=models.CASCADE,
        related_name='user_links',
        verbose_name='Роль',
    )

    class Meta:
        verbose_name = 'Роль пользователя в проекте'
        verbose_name_plural = 'Роли пользователей в проекте'
        unique_together = [('project', 'user', 'role')]
        indexes = [
            models.Index(fields=['project', 'user']),
        ]

    def __str__(self) -> str:
        return f'{self.project_id}:{self.user_id}:{self.role_id}'


class ProjectAuditLog(models.Model):
    """Модель для отслеживания аудита изменений в проекте.
    
    Записывает все изменения полей проекта, связанных моделей и действий пользователей.
    Позволяет восстановить историю изменений и отследить, кто и когда что изменил.
    """

    class ActionType(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Обновление'
        DELETE = 'delete', 'Удаление'
        STATUS_CHANGE = 'status_change', 'Изменение статуса'
        ROLE_ASSIGN = 'role_assign', 'Назначение роли'
        ROLE_REMOVE = 'role_remove', 'Удаление роли'
        BUDGET_CHANGE = 'budget_change', 'Изменение бюджета'
        STAGE_ADD = 'stage_add', 'Добавление этапа'
        STAGE_UPDATE = 'stage_update', 'Обновление этапа'
        STAGE_DELETE = 'stage_delete', 'Удаление этапа'

    class ModelType(models.TextChoices):
        PROJECT = 'project', 'Проект'
        PROJECT_TASK = 'project_task', 'Задача проекта'
        PROJECT_EXECUTOR = 'project_executor', 'Исполнитель проекта'
        PROJECT_PLANNED_RESULT = 'project_planned_result', 'Планируемый результат'
        PROJECT_TARGET_INDICATOR = 'project_target_indicator', 'Целевой показатель'
        PROJECT_STAGE = 'project_stage', 'Этап проекта'
        PROJECT_BUDGET_ITEM = 'project_budget_item', 'Бюджетная позиция'
        PROJECT_BUDGET_TOTAL = 'project_budget_total', 'Бюджет итого'
        PROJECT_USER_ROLE = 'project_user_role', 'Роль пользователя'

    # Связь с проектом
    project = models.ForeignKey(
        'project_ed.Project',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name='Проект'
    )
    
    # Связь с пользователем, который выполнил действие
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_ed_audit_logs',
        verbose_name='Пользователь'
    )
    
    # Тип действия
    action = models.CharField(
        'Действие',
        max_length=32,
        choices=ActionType.choices
    )
    
    # Тип модели, которая была изменена
    model_type = models.CharField(
        'Тип модели',
        max_length=32,
        choices=ModelType.choices,
        default=ModelType.PROJECT
    )
    
    # ID объекта, который был изменен (может быть None для создания)
    object_id = models.PositiveIntegerField(
        'ID объекта',
        null=True,
        blank=True
    )
    
    # Название поля, которое было изменено (для UPDATE действий)
    field_name = models.CharField(
        'Название поля',
        max_length=255,
        blank=True,
        default=''
    )
    
    # Старое значение поля (для UPDATE действий)
    old_value = models.TextField(
        'Старое значение',
        blank=True,
        default=''
    )
    
    # Новое значение поля (для UPDATE действий)
    new_value = models.TextField(
        'Новое значение',
        blank=True,
        default=''
    )
    
    # Дополнительная информация о действии (JSON)
    metadata = models.JSONField(
        'Метаданные',
        default=dict,
        blank=True
    )
    
    # IP адрес пользователя (если доступен)
    ip_address = models.GenericIPAddressField(
        'IP адрес',
        null=True,
        blank=True
    )
    
    # User-Agent браузера (если доступен)
    user_agent = models.TextField(
        'User-Agent',
        blank=True,
        default=''
    )
    
    # Время выполнения действия
    timestamp = models.DateTimeField(
        'Время действия',
        auto_now_add=True
    )
    
    # Дополнительное описание действия
    description = models.TextField(
        'Описание',
        blank=True,
        default=''
    )

    class Meta:
        verbose_name = 'Запись аудита проекта'
        verbose_name_plural = 'Записи аудита проекта'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['project', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model_type', 'object_id']),
        ]

    def __str__(self) -> str:
        return f'{self.project_id}: {self.get_action_display()} - {self.get_model_type_display()} ({self.timestamp.strftime("%d.%m.%Y %H:%M")})'

    @classmethod
    def log_action(
        cls,
        project,
        action,
        user=None,
        model_type=ModelType.PROJECT,
        object_id=None,
        field_name='',
        old_value='',
        new_value='',
        metadata=None,
        ip_address=None,
        user_agent='',
        description=''
    ):
        """Удобный метод для создания записи аудита."""
        return cls.objects.create(
            project=project,
            user=user,
            action=action,
            model_type=model_type,
            object_id=object_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            description=description
        )