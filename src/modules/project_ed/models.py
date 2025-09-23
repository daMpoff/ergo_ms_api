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
    
    # Связь с блоком мероприятий
    event_block = models.ForeignKey(
        'EventBlock',
        on_delete=models.SET_NULL,
        related_name='target_indicators',
        verbose_name='Блок мероприятий',
        null=True,
        blank=True
    )
    
    # Ответственный
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='responsible_indicators',
        verbose_name='Ответственный',
        null=True,
        blank=True
    )
    
    # Значения по годам (JSON поле)
    values_by_year = models.JSONField('Значения по годам', default=dict, blank=True)
    
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
    
    code = models.CharField('Код блока', max_length=50, blank=True, null=True)
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
    
    def save(self, *args, **kwargs):
        """Переопределяем save для обновления кодов мероприятий при изменении кода блока."""
        # Проверяем, изменился ли код блока
        if self.pk:
            try:
                old_instance = EventBlock.objects.get(pk=self.pk)
                old_code = old_instance.code
                new_code = self.code
                
                # Если код изменился и новый код не пустой, обновляем коды мероприятий
                if old_code != new_code and new_code:
                    self._update_events_codes(old_code, new_code)
            except EventBlock.DoesNotExist:
                pass  # Объект не существует, пропускаем
        
        super().save(*args, **kwargs)
    
    def _update_events_codes(self, old_code, new_code):
        """Обновляет коды всех мероприятий в блоке при изменении кода блока."""
        import re
        from django.db import transaction
        
        # Получаем все мероприятия в блоке
        events = self.events.filter(is_active=True)
        
        with transaction.atomic():
            for event in events:
                if event.code:
                    # Пытаемся извлечь номер мероприятия из кода
                    # Сначала пробуем паттерн с кодом блока
                    pattern_with_block = re.escape(old_code) + r'\.(\d+)$'
                    match = re.match(pattern_with_block, event.code)
                    
                    if match:
                        # Код соответствует старому коду блока
                        event_number = match.group(1)
                        new_event_code = f"{new_code}.{event_number}"
                    else:
                        # Код не соответствует коду блока, извлекаем номер из любого паттерна X.Y
                        general_pattern = r'^(.+)\.(\d+)$'
                        general_match = re.match(general_pattern, event.code)
                        
                        if general_match:
                            # Используем номер из существующего кода
                            event_number = general_match.group(2)
                            new_event_code = f"{new_code}.{event_number}"
                        else:
                            # Если код не соответствует ни одному паттерну, генерируем новый
                            # Находим максимальный номер в блоке
                            max_number = 0
                            for other_event in events:
                                if other_event.code and other_event.id != event.id:
                                    other_match = re.match(r'^.+\.(\d+)$', other_event.code)
                                    if other_match:
                                        number = int(other_match.group(1))
                                        if number > max_number:
                                            max_number = number
                            
                            new_number = max_number + 1
                            new_event_code = f"{new_code}.{new_number}"
                    
                    event.code = new_event_code
                    event.save(update_fields=['code', 'updated_at'])


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


class Role(models.Model):
    name = models.CharField('Название', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Роль ProjectEd'
        verbose_name_plural = 'Роли ProjectEd'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Position(models.Model):
    name = models.CharField('Название', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Должность ProjectEd'
        verbose_name_plural = 'Должности ProjectEd'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Faculty(models.Model):
    name = models.CharField('Название', max_length=255, unique=True)
    short_name = models.CharField('Сокращённое название', max_length=10, blank=True, default='')

    class Meta:
        verbose_name = 'Факультет ProjectEd'
        verbose_name_plural = 'Факультеты ProjectEd'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    name = models.CharField('Название', max_length=255, unique=True)
    short_name = models.CharField('Сокращённое название', max_length=10, blank=True, default='')
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments',
        verbose_name='Факультет'
    )

    class Meta:
        verbose_name = 'Кафедра ProjectEd'
        verbose_name_plural = 'Кафедры ProjectEd'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name