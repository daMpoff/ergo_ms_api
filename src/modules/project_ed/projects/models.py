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