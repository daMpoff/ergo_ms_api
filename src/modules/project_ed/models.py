from django.db import models
from django.conf import settings


class Project(models.Model):
    """Проект (Project), созданный пользователем через многоэтапную форму.

    Центральная сущность хранит все данные формы в JSON-полях, чтобы гибко
    поддерживать динамическую структуру фронтенда без сложной схемы БД.
    """

    # Пользователь, создавший проект
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_ed_projects',
        verbose_name='Владелец проекта'
    )

    # Основные поля паспорта проекта (для быстрого поиска и отображения)
    short_name = models.CharField('Краткое наименование', max_length=255)
    name = models.TextField('Наименование проекта')
    name_clarification = models.CharField('Уточняющее наименование', max_length=255, blank=True)

    # Даты проекта
    start_date = models.DateField('Дата начала проекта')
    end_date = models.DateField('Дата окончания проекта')

    # Роли/участники (в минимальной форме – как текстовые/числовые идентификаторы)
    curator_id = models.IntegerField('Куратор (ID)', null=True, blank=True)
    customer_name = models.CharField('Заказчик', max_length=255, blank=True)
    manager_name = models.CharField('Руководитель проекта', max_length=255, blank=True)

    # Быстрые агрегаты
    budget_total = models.DecimalField('Бюджет (с учетом взносов)', max_digits=12, decimal_places=2, default=0)

    # Сырые структуры формы
    event = models.JSONField('Выбранное мероприятие', null=True, blank=True)
    basic_provisions = models.JSONField('Основные положения', default=dict)
    target_indicators = models.JSONField('Целевые показатели', default=list)
    calendar_plan = models.JSONField('Календарный план', default=dict)
    budget = models.JSONField('Бюджет', default=dict)
    additional_info = models.JSONField('Дополнительная информация', default=dict)

    # Служебные поля
    status = models.CharField('Статус', max_length=32, default='draft')  # draft, pending, rejected, active, done
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.short_name or f'Project #{self.pk}'