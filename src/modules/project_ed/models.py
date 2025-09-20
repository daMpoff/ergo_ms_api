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


class Category(models.Model):
    """Категория показателей проекта."""
    
    name = models.CharField('Название категории', max_length=255)
    description = models.TextField('Описание категории', blank=True)
    order = models.PositiveIntegerField('Порядок сортировки', default=0)
    is_active = models.BooleanField('Активна', default=True)
    
    # Служебные поля
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Категория показателей'
        verbose_name_plural = 'Категории показателей'
        ordering = ['order', 'name']
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def indicators_count(self):
        """Количество целевых показателей в этой категории."""
        return self.target_indicators.count()
    
    @property
    def subcategories_count(self):
        """Количество подкатегорий."""
        return self.subcategories.count()


class Subcategory(models.Model):
    """Подкатегория показателей проекта."""
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name='Категория'
    )
    name = models.CharField('Название подкатегории', max_length=255)
    description = models.TextField('Описание подкатегории', blank=True)
    order = models.PositiveIntegerField('Порядок сортировки', default=0)
    is_active = models.BooleanField('Активна', default=True)
    
    # Служебные поля
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Подкатегория показателей'
        verbose_name_plural = 'Подкатегории показателей'
        ordering = ['order', 'name']
        unique_together = ['category', 'name']
    
    def __str__(self) -> str:
        return f'{self.category.name} - {self.name}'
    
    @property
    def indicators_count(self):
        """Количество целевых показателей в этой подкатегории."""
        return self.target_indicators.count()


class TargetIndicator(models.Model):
    """Целевой показатель проекта."""
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_target_indicators',
        verbose_name='Проект'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='target_indicators',
        verbose_name='Категория',
        null=True,
        blank=True
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.CASCADE,
        related_name='target_indicators',
        verbose_name='Подкатегория',
        null=True,
        blank=True
    )
    
    name = models.CharField('Название показателя', max_length=255)
    description = models.TextField('Описание показателя', blank=True)
    unit = models.CharField('Единица измерения', max_length=50, blank=True)
    target_value = models.DecimalField('Целевое значение', max_digits=10, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField('Текущее значение', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Служебные поля
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Целевой показатель'
        verbose_name_plural = 'Целевые показатели'
        ordering = ['category__order', 'subcategory__order', 'name']
    
    def __str__(self) -> str:
        return self.name
    
    def clean(self):
        """Валидация: подкатегория должна принадлежать выбранной категории."""
        from django.core.exceptions import ValidationError
        
        if self.subcategory and self.category and self.subcategory.category != self.category:
            raise ValidationError('Подкатегория должна принадлежать выбранной категории.')


class EventBlock(models.Model):
    """Блок мероприятий программы развития БГТУ."""
    
    title = models.CharField('Название блока', max_length=255)
    description = models.TextField('Описание блока', blank=True)
    
    # Связь с категорией и подкатегорией (опционально)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='event_blocks',
        verbose_name='Категория',
        null=True,
        blank=True
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        related_name='event_blocks',
        verbose_name='Подкатегория',
        null=True,
        blank=True
    )
    
    # Служебные поля
    order = models.PositiveIntegerField('Порядок сортировки', default=0)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Блок мероприятий'
        verbose_name_plural = 'Блоки мероприятий'
        ordering = ['order', 'title']
    
    def __str__(self) -> str:
        return self.title
    
    @property
    def category_name(self):
        """Название категории."""
        return self.category.name if self.category else None
    
    @property
    def subcategory_name(self):
        """Название подкатегории."""
        return self.subcategory.name if self.subcategory else None
    
    @property
    def events_count(self):
        """Количество мероприятий в блоке."""
        return self.events.count()
    
    def clean(self):
        """Валидация: подкатегория должна принадлежать выбранной категории."""
        from django.core.exceptions import ValidationError
        
        if self.subcategory and self.category and self.subcategory.category != self.category:
            raise ValidationError('Подкатегория должна принадлежать выбранной категории.')


class Event(models.Model):
    """Мероприятие в блоке мероприятий."""
    
    block = models.ForeignKey(
        EventBlock,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Блок мероприятий'
    )
    
    code = models.CharField('Код мероприятия', max_length=50, blank=True)
    name = models.CharField('Наименование мероприятия', max_length=500)
    results = models.TextField('Основные результаты', blank=True)
    
    # Сроки реализации
    start_year = models.PositiveIntegerField('Год начала', null=True, blank=True)
    end_year = models.PositiveIntegerField('Год окончания', null=True, blank=True)
    
    # Служебные поля
    order = models.PositiveIntegerField('Порядок сортировки', default=0)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'
        ordering = ['block__order', 'order', 'name']
    
    def __str__(self) -> str:
        return f'{self.code} - {self.name}' if self.code else self.name
    
    @property
    def years_display(self):
        """Отображение годов реализации."""
        if self.start_year and self.end_year:
            if self.start_year == self.end_year:
                return str(self.start_year)
            return f'{self.start_year}–{self.end_year}'
        elif self.start_year:
            return f'с {self.start_year}'
        elif self.end_year:
            return f'до {self.end_year}'
        return ''
    
    def clean(self):
        """Валидация: год начала не может быть больше года окончания."""
        from django.core.exceptions import ValidationError
        
        if self.start_year and self.end_year and self.start_year > self.end_year:
            raise ValidationError('Год начала не может быть больше года окончания.')