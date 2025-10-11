from django.db import models
from django.conf import settings
from django.utils import timezone


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
# --- Модели для экспертной проверки проектов ---

class ProjectReview(models.Model):
    """Экспертная проверка проекта.
    
    Создается автоматически при отправке проекта на проверку экспертной группой.
    Отслеживает статус проверки и общие результаты экспертизы.
    """
    
    class ReviewStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает проверки'
        IN_PROGRESS = 'in_progress', 'В процессе проверки'
        APPROVED = 'approved', 'Одобрен'
        REJECTED = 'rejected', 'Отклонен'
        NEEDS_REVISION = 'needs_revision', 'Требует доработки'
    
    project = models.ForeignKey(
        'project_ed.Project',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Проект'
    )
    
    version = models.ForeignKey(
        ProjectVersion,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Версия проекта',
        help_text='Версия проекта, которая проверяется'
    )
    
    status = models.CharField(
        'Статус проверки',
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING
    )
    
    # Даты
    started_at = models.DateTimeField('Начата', null=True, blank=True)
    completed_at = models.DateTimeField('Завершена', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Экспертная проверка проекта'
        verbose_name_plural = 'Экспертные проверки проектов'
        ordering = ['started_at']
    
    def __str__(self) -> str:
        version_info = f'v{self.version.version_number}' if self.version else 'без версии'
        return f'Проверка проекта #{self.project_id} {version_info} - {self.get_status_display()}'
    
    @property
    def experts_count(self):
        """Общее количество экспертов, назначенных на эту проверку."""
        return self.assigned_experts.count()
    
    @property
    def decided_experts_count(self):
        """Количество экспертов, которые уже приняли решение."""
        return self.decisions.count()
    
    @property
    def pending_experts_count(self):
        """Количество экспертов, которые еще не приняли решение."""
        return self.experts_count - self.decided_experts_count
    
    @property
    def started_experts_count(self):
        """Количество экспертов, которые начали проверку."""
        return self.assigned_experts.filter(
            status__in=[ProjectReviewExpert.ExpertStatus.STARTED, 
                       ProjectReviewExpert.ExpertStatus.COMPLETED]
        ).count()
    
    @property
    def completed_experts_count(self):
        """Количество экспертов, которые завершили проверку."""
        return self.assigned_experts.filter(
            status=ProjectReviewExpert.ExpertStatus.COMPLETED
        ).count()
    
    def assign_experts(self):
        """Автоматически назначить всех экспертов из 'Экспертная группа' на эту проверку."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        experts = User.objects.filter(
            project_ed_profile__role_ref__name='Экспертная группа'
        )
        
        for expert in experts:
            ProjectReviewExpert.objects.get_or_create(
                review=self,
                expert=expert,
                defaults={'status': ProjectReviewExpert.ExpertStatus.ASSIGNED}
            )
    
    @classmethod
    def create_for_project_version(cls, project, version):
        """Создать проверку для конкретной версии проекта.
        
        Args:
            project: Экземпляр проекта
            version: Экземпляр версии проекта
            
        Returns:
            ProjectReview: Созданная проверка
        """
        review = cls.objects.create(
            project=project,
            version=version,
            status=cls.ReviewStatus.PENDING,
            started_at=timezone.now()
        )
        
        # Автоматически назначаем экспертов
        review.assign_experts()
        
        return review
    
    @property
    def version_info(self):
        """Получить информацию о версии проекта."""
        if not self.version:
            return None
            
        return {
            'version_number': self.version.version_number,
            'title': self.version.title,
            'created_at': self.version.created_at,
            'created_by': str(self.version.created_by) if self.version.created_by else None
        }


class ProjectReviewExpert(models.Model):
    """Связь эксперта с проверкой проекта.
    
    Определяет, какие конкретные эксперты назначены для проверки конкретного проекта.
    Создается автоматически при отправке проекта на проверку.
    """
    
    class ExpertStatus(models.TextChoices):
        ASSIGNED = 'assigned', 'Назначен'
        STARTED = 'started', 'Начал проверку'
        COMPLETED = 'completed', 'Завершил проверку'
    
    review = models.ForeignKey(
        ProjectReview,
        on_delete=models.CASCADE,
        related_name='assigned_experts',
        verbose_name='Проверка проекта'
    )
    
    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_review_assignments',
        verbose_name='Эксперт'
    )
    
    status = models.CharField(
        'Статус эксперта',
        max_length=32,
        choices=ExpertStatus.choices,
        default=ExpertStatus.ASSIGNED
    )
    
    assigned_at = models.DateTimeField('Назначен', auto_now_add=True)
    started_at = models.DateTimeField('Начал проверку', null=True, blank=True)
    completed_at = models.DateTimeField('Завершил проверку', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Эксперт проверки проекта'
        verbose_name_plural = 'Эксперты проверки проекта'
        unique_together = [('review', 'expert')]
        ordering = ['assigned_at']
    
    def __str__(self) -> str:
        return f'{self.expert.username} - {self.review.project.title}'


class ProjectReviewComment(models.Model):
    """Замечание эксперта по конкретному пункту проекта.
    
    Упрощенная модель с JSON структурой для хранения всех данных о замечании.
    Это обеспечивает гибкость и простоту использования, соответствуя структуре
    данных проекта из frontend.
    """
    
    review = models.ForeignKey(
        ProjectReview,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Проверка проекта'
    )
    
    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_review_comments',
        verbose_name='Эксперт'
    )
    
    # Основные данные замечания в JSON
    comment_data = models.JSONField(
        'Данные замечания',
        default=dict,
        help_text='''JSON структура с данными замечания:
        {
            "section": "basic_provisions",           // Раздел проекта
            "field": "projectName",                  // Поле проекта
            "fieldDisplay": "Наименование проекта",  // Отображаемое название
            "elementType": "field",                  // Тип элемента (field, task, stage, etc.)
            "elementIndex": 0,                       // Индекс в массиве (если применимо)
            "elementName": "Анализ требований",      // Название элемента
            "elementPath": "projectTasks[0]",        // JSONPath к элементу
            
            "type": "warning",                       // Тип: critical, warning, suggestion, question, info
            "priority": "medium",                    // Приоритет: low, medium, high, critical
            "title": "Заголовок замечания",
            "text": "Текст замечания",
            
            "oldValue": "Старое значение",           // Значение до исправления
            "suggestedValue": "Предлагаемое значение", // Предлагаемое исправление
            
            "relatedObject": {                       // Связанный объект (если применимо)
                "type": "project_task",
                "id": 123
            },
            
            "metadata": {                            // Дополнительные данные
                "context": "Контекст замечания",
                "references": ["ссылка1", "ссылка2"]
            }
        }'''
    )
    
    # Статус исправления
    is_resolved = models.BooleanField('Исправлено', default=False)
    resolved_at = models.DateTimeField('Исправлено', null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_project_comments',
        verbose_name='Исправил'
    )
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Замечание эксперта'
        verbose_name_plural = 'Замечания экспертов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['review', 'is_resolved']),
            models.Index(fields=['expert', 'created_at']),
        ]
    
    def __str__(self) -> str:
        data = self.comment_data
        section = data.get('section', 'Неизвестный раздел')
        field_display = data.get('fieldDisplay', 'Неизвестное поле')
        title = data.get('title', 'Без заголовка')
        
        element_info = ''
        if data.get('elementType') != 'field':
            if data.get('elementName'):
                element_info = f' ({data["elementName"]})'
            elif data.get('elementIndex') is not None:
                element_info = f' (элемент #{data["elementIndex"] + 1})'
        
        return f'{section} - {field_display}{element_info}: {title}'
    
    # Удобные свойства для доступа к данным
    @property
    def section(self):
        """Раздел проекта."""
        return self.comment_data.get('section', '')
    
    @property
    def field(self):
        """Поле проекта."""
        return self.comment_data.get('field', '')
    
    @property
    def field_display(self):
        """Отображаемое название поля."""
        return self.comment_data.get('fieldDisplay', '')
    
    @property
    def element_type(self):
        """Тип элемента."""
        return self.comment_data.get('elementType', 'field')
    
    @property
    def element_index(self):
        """Индекс элемента в массиве."""
        return self.comment_data.get('elementIndex')
    
    @property
    def element_name(self):
        """Название элемента."""
        return self.comment_data.get('elementName', '')
    
    @property
    def element_path(self):
        """Путь к элементу."""
        return self.comment_data.get('elementPath', '')
    
    @property
    def comment_type(self):
        """Тип замечания."""
        return self.comment_data.get('type', 'warning')
    
    @property
    def priority(self):
        """Приоритет замечания."""
        return self.comment_data.get('priority', 'medium')
    
    @property
    def title(self):
        """Заголовок замечания."""
        return self.comment_data.get('title', '')
    
    @property
    def text(self):
        """Текст замечания."""
        return self.comment_data.get('text', '')
    
    @property
    def old_value(self):
        """Старое значение."""
        return self.comment_data.get('oldValue', '')
    
    @property
    def suggested_value(self):
        """Предлагаемое значение."""
        return self.comment_data.get('suggestedValue', '')
    
    @property
    def related_object(self):
        """Связанный объект."""
        return self.comment_data.get('relatedObject', {})
    
    @property
    def metadata(self):
        """Метаданные."""
        return self.comment_data.get('metadata', {})
    
    # Проверки
    @property
    def is_critical(self):
        """Проверяет, является ли замечание критичным."""
        return (self.comment_type == 'critical' or 
                self.priority == 'critical')
    
    @property
    def is_high_priority(self):
        """Проверяет, является ли замечание высокоприоритетным."""
        return self.priority in ['high', 'critical']
    
    @property
    def display_path(self):
        """Возвращает читаемый путь к элементу."""
        if not self.element_path:
            return self.field_display
        
        return f"{self.field_display} → {self.element_path}"
    
    # Методы создания замечаний
    @classmethod
    def create_comment(
        cls,
        review,
        expert,
        comment_data,
        is_resolved=False
    ):
        """Создать замечание с JSON данными."""
        return cls.objects.create(
            review=review,
            expert=expert,
            comment_data=comment_data,
            is_resolved=is_resolved
        )
    
    @classmethod
    def create_for_field(
        cls,
        review,
        expert,
        section,
        field,
        field_display,
        title,
        text,
        old_value='',
        suggested_value='',
        comment_type='warning',
        priority='medium',
        metadata=None
    ):
        """Создать замечание для конкретного поля проекта."""
        comment_data = {
            'section': section,
            'field': field,
            'fieldDisplay': field_display,
            'elementType': 'field',
            'type': comment_type,
            'priority': priority,
            'title': title,
            'text': text,
            'oldValue': old_value,
            'suggestedValue': suggested_value,
            'metadata': metadata or {}
        }
        
        return cls.create_comment(review, expert, comment_data)
    
    @classmethod
    def create_for_array_item(
        cls,
        review,
        expert,
        section,
        field,
        field_display,
        element_type,
        element_index,
        element_name,
        title,
        text,
        old_value='',
        suggested_value='',
        comment_type='warning',
        priority='medium',
        metadata=None
    ):
        """Создать замечание для элемента массива."""
        element_path = f"{field}[{element_index}]"
        
        comment_data = {
            'section': section,
            'field': field,
            'fieldDisplay': field_display,
            'elementType': element_type,
            'elementIndex': element_index,
            'elementName': element_name,
            'elementPath': element_path,
            'type': comment_type,
            'priority': priority,
            'title': title,
            'text': text,
            'oldValue': old_value,
            'suggestedValue': suggested_value,
            'metadata': metadata or {}
        }
        
        return cls.create_comment(review, expert, comment_data)
    
    @classmethod
    def create_for_related_object(
        cls,
        review,
        expert,
        section,
        field,
        field_display,
        related_object_type,
        related_object_id,
        title,
        text,
        comment_type='warning',
        priority='medium',
        metadata=None
    ):
        """Создать замечание, связанное с объектом проекта."""
        comment_data = {
            'section': section,
            'field': field,
            'fieldDisplay': field_display,
            'elementType': 'related_object',
            'type': comment_type,
            'priority': priority,
            'title': title,
            'text': text,
            'relatedObject': {
                'type': related_object_type,
                'id': related_object_id
            },
            'metadata': metadata or {}
        }
        
        return cls.create_comment(review, expert, comment_data)


class ProjectReviewDecision(models.Model):
    """Решение эксперта по проекту.
    
    Каждый эксперт принимает одно из трех решений:
    - Одобрить проект
    - Отклонить проект  
    - Требует доработки
    """
    
    class Decision(models.TextChoices):
        APPROVE = 'approve', 'Одобрить'
        REJECT = 'reject', 'Отклонить'
        NEEDS_REVISION = 'needs_revision', 'Требует доработки'
    
    review = models.ForeignKey(
        ProjectReview,
        on_delete=models.CASCADE,
        related_name='decisions',
        verbose_name='Проверка проекта'
    )
    
    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_review_decisions',
        verbose_name='Эксперт'
    )
    
    decision = models.CharField(
        'Решение',
        max_length=32,
        choices=Decision.choices
    )
    
    comment = models.TextField('Комментарий к решению', blank=True, default='')
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Решение эксперта'
        verbose_name_plural = 'Решения экспертов'
        unique_together = ['review', 'expert']
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f'{self.expert.username}: {self.get_decision_display()}'