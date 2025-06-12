from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from src.external.learning_analytics.models import (
    Employer
)

# Модель ImportHistory хранит записи истории импорта данных.
class ImportHistory(models.Model):
    """
    Модель ImportHistory хранит записи истории импорта данных.
    
    Attributes:
        timestamp (DateTimeField): Дата и время импорта
        data_type (CharField): Тип импортируемых данных
        file_name (CharField): Имя импортируемого файла
        records_count (PositiveIntegerField): Количество записей в файле
        status (CharField): Статус импорта (успех, предупреждение, ошибка)
    """
    DATA_TYPE_CHOICES = [
        ('curriculum', 'Учебный план'),
        ('competencies', 'Компетенции'),
        ('technologies', 'Технологии'),
        ('vacancies', 'Вакансии'),
        ('custom', 'Пользовательский формат'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('warning', 'С предупреждениями'),
        ('error', 'С ошибками'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время импорта")
    data_type = models.CharField(max_length=50, choices=DATA_TYPE_CHOICES, verbose_name="Тип данных")
    file_name = models.CharField(max_length=255, verbose_name="Имя файла")
    records_count = models.PositiveIntegerField(verbose_name="Количество записей", validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Статус импорта")
    
    def __str__(self):
        return f"{self.file_name} ({self.timestamp.strftime('%d.%m.%Y %H:%M')})"
    
    class Meta:
        verbose_name = "История импорта"
        verbose_name_plural = "История импортов"
        db_table = "la_df_import_history"
        ordering = ["-timestamp"]

# Модель ImportStats хранит статистику импорта данных.
class ImportStats(models.Model):
    """
    Модель ImportStats хранит статистику импорта данных.
     
    Attributes:
        sum_of_imported_files (PositiveIntegerField): Количество импортированных файлов.
        sum_of_imported_records (PositiveIntegerField): Количество импортированных записей.
        last_file_timestamp (DateTimeField): Дата и время последнего импортированного файла.
    """

    sum_of_imported_files = models.PositiveIntegerField(verbose_name="Количество импортированных файлов", default=0)
    sum_of_imported_records = models.PositiveIntegerField(verbose_name="Количество импортированных записей", default=0)
    last_file_timestamp = models.DateTimeField(verbose_name="Дата и время последнего импортированного файла", null=True, blank=True)

    def __str__(self):
        return f"Статистика импорта данных: {self.sum_of_imported_files} файлов, {self.sum_of_imported_records} записей, последний импорт: {self.last_file_timestamp}"
    
    @classmethod
    def get_or_create_initial_stats(cls):
        """
        Получает существующую запись статистики импорта или создает новую с нулевыми значениями.
        Гарантирует наличие записи в таблице.
        """
        try:
            stats = cls.objects.first()
            if not stats:
                stats = cls.objects.create(
                    sum_of_imported_files=0,
                    sum_of_imported_records=0,
                    last_file_timestamp=None
                )
            return stats
        except Exception as e:
            # В случае ошибки создаем новую запись
            return cls.objects.create(
                sum_of_imported_files=0,
                sum_of_imported_records=0,
                last_file_timestamp=None
            )
    
    class Meta:
        verbose_name = "Статистика импорта данных"
        verbose_name_plural = "Статистика импорта данных"
        db_table = "la_df_import_stats"

# Модель специальности (для обучающегося студента).
class Speciality(models.Model):
    """
    Модель Speciality представляет собой информацию о специальности (направлении подготовки).

    Attributes:
        code (CharField): Код специальности. Максимальная длина — 20 символов, уникальный.
        name (CharField): Наименование специальности. Максимальная длина — 255 символов.
        specialization (CharField): Наименование специализации. Максимальная длина - 255 символов.
        department (CharField): Кафедра, выпускающая специальность. Максимальная длина - 255 символов.
        faculty (CharField): Факультет. Максимальная длина - 255 символов.
    """
    code = models.CharField(max_length=20, verbose_name="Код специальности")
    name = models.CharField(max_length=255, verbose_name="Специальность")
    specialization = models.CharField(max_length=255, verbose_name="Специализация")
    department = models.CharField(max_length=255, verbose_name="Кафедра")
    faculty = models.CharField(max_length=255, verbose_name="Факультет")

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Специальность"
        verbose_name_plural = "Специальности"
        db_table = "la_df_speciality" 

class Curriculum(models.Model):
    """
    Модель Curriculum представляет собой учебный план специальности.

    Attributes:
        speciality (ForeignKey): Внешний ключ на модель Speciality, может быть пустым.
        education_duration (PositiveSmallIntegerField): Срок получения образования.
        year_of_admission (CharField): Год поступления. Максимальная длина - 4 символа.
        is_active (BooleanField): Флаг актуальности учебного плана. По умолчанию True.
    """
    speciality = models.ForeignKey(
        Speciality,
        on_delete=models.CASCADE,
        verbose_name="Специальность",
        blank=True,
        null=True
    )
    education_duration = models.PositiveSmallIntegerField(verbose_name="Срок получения образования")
    year_of_admission = models.CharField(max_length=4, verbose_name="Год поступления")
    is_active = models.BooleanField(default=True, verbose_name="Актуальность учебного плана")

    def __str__(self):
        return f"Учебный план для {self.speciality}"

    class Meta:
        verbose_name = "Учебный план"
        verbose_name_plural = "Учебные планы"
        db_table = "la_df_curriculum"

# Модель Technology представляет ту или иную технологию, осваиваемую в процессе изучения дисциплин.
class Technology(models.Model):
    """
    Модель Technology представляет технологию, осваиваемую в процессе изучения дисциплин.

    Attributes:
        name (CharField): Название технологии. Максимальная длина — 60 символов.
        description (TextField): Описание технологии. Максимальная длина — 400 символов.
        popularity (DecimalField): Уровень популярности технологии от 0 до 100, %. 4 цифры, 2 после запятой.
        rating (DecimalField): Рейтинг технологии от 0 до 5. 3 цифры, 2 после запятой.
    """
    name = models.CharField(max_length=60)
    description = models.TextField(max_length=400)
    popularity = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    def __str__(self):
        return f"{self.name} - {self.description}"

    class Meta:
        verbose_name = "Технология"
        verbose_name_plural = "Технологии"
        db_table = "la_df_technology" 

# Модель Competency представляет компетенции 
class Competency(models.Model):
    """
    Модель Competency представляет компетенции.

    Attributes:
        code (CharField): Уникальный код компетенции. Максимальная длина — 10 символов.
        name (CharField): Название компетенции. Максимальная длина — 200 символов.
        description (TextField): Описание компетенции. Максимальная длина — 400 символов.
        know_level (TextField): Уровень освоения компетенции по метрике "Знать".
        can_level (TextField): Уровень освоения компетенции по метрике "Уметь".
        master_level (TextField): Уровень освоения компетенции по метрике "Владеть".
        blooms_level (CharField): Уровень по таксономии Блума.
        blooms_verbs (CharField): Глаголы действий для оценки уровня.
        complexity (PositiveIntegerField): Сложность компетенции (1-10).
        demand (PositiveIntegerField): Востребованность компетенции (1-10).
    """
    BLOOMS_LEVELS = [
        ('KNOW', 'Знание'),
        ('UNDERSTAND', 'Понимание'),
        ('APPLY', 'Применение'),
        ('ANALYZE', 'Анализ'),
        ('EVALUATE', 'Оценка'),
        ('CREATE', 'Создание'),
    ]


    code = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=400)

    # Уровни освоения компетенции
    know_level = models.TextField(verbose_name="Знать", help_text="Теоретические знания")
    can_level = models.TextField(verbose_name="Уметь", help_text="Практические навыки")
    master_level = models.TextField(verbose_name="Владеть", help_text="Способность к выполнению задач")

    # Таксономия Блума
    blooms_level = models.CharField(
        choices=BLOOMS_LEVELS,
        default='KNOW',
        verbose_name="Уровень таксономии Блума"
    )
    blooms_verbs = models.CharField(
        max_length=255,
        verbose_name="Глаголы для оценки таксономии Блума",
        help_text="Через запятую: анализировать, оценивать, создавать и т.д."
    )
    
    complexity = models.PositiveIntegerField(
        verbose_name="Сложность",
        help_text="Сложность компетенции от 1 до 10",
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10)
        ]
    )
    demand = models.PositiveIntegerField(
        verbose_name="Востребованность",
        help_text="Востребованность компетенции от 1 до 10",
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10)
        ]
    )

    class Meta:
        verbose_name = "Компетенция"
        verbose_name_plural = "Компетенции"
        db_table = "la_df_competency"


    def __str__(self):
        return f"{self.code} ({self.name})" 

# Модель базовой дисциплины (справочник)
class BaseDiscipline(models.Model):
    """
    Модель BaseDiscipline представляет собой справочник базовых дисциплин.

    Attributes:
        code (CharField): Код дисциплины. Максимальная длина - 10 символов, уникальный.
        name (CharField): Наименование дисциплины. Максимальная длина - 255 символов.
        description (TextField): Описание дисциплины. Максимальная длина - 400 символов.
    """
    code = models.CharField(max_length=10, unique=True, verbose_name="Код дисциплины")
    name = models.CharField(max_length=255, verbose_name="Наименование")
    description = models.TextField(max_length=400, verbose_name="Описание")

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Базовая дисциплина"
        verbose_name_plural = "Базовые дисциплины"
        db_table = "la_df_base_discipline"

# Модель дисциплины
class Discipline(models.Model):
    """
    Модель Discipline представляет собой информацию о дисциплине.
    
    Attributes:
        curriculum (ForeignKey): Связь с моделью Curriculum, может быть пустым.
        base_discipline (ForeignKey): Связь с моделью BaseDiscipline, может быть пустым.
        code (CharField): Код дисциплины. Максимальная длина - 10 символов, уникальный.
        name (CharField): Наименование дисциплины. Максимальная длина - 255 символов.
        semesters (CharField): Период освоения дисциплины (номера семестров через ','). Максимальная длина - 12 символов.
        contact_work_hours (PositiveSmallIntegerField): Длительность контактной работы, часы.
        independent_work_hours (PositiveSmallIntegerField): Длительность самостоятельной работы, часы.
        control_work_hours (PositiveSmallIntegerField): Длительность контроля, часы.
        technologies (ManyToManyField): Связь с моделью Technology.
        competencies (ManyToManyField): Связь с моделью Competency.
    """
    curriculum = models.ForeignKey(Curriculum, verbose_name="Учебный план", on_delete=models.CASCADE, blank=True, null=True, related_name="curriculum_disciplines")
    base_discipline = models.ForeignKey(BaseDiscipline, verbose_name="Базовая дисциплина", on_delete=models.CASCADE, blank=True, null=True, related_name="base_discipline")
    code = models.CharField(max_length=10, unique=True, verbose_name="Код дисциплины")
    name = models.CharField(max_length=255, verbose_name="Наименование")
    semesters = models.CharField(max_length=12, verbose_name="Период освоения (семестры)")
    contact_work_hours = models.PositiveSmallIntegerField(verbose_name="Контактная работа, ч")
    independent_work_hours = models.PositiveSmallIntegerField(verbose_name="Самостоятельная работа, ч")
    control_work_hours = models.PositiveSmallIntegerField(verbose_name="Контроль, ч")
    technologies = models.ManyToManyField(Technology, verbose_name="Технологии", blank=True, related_name="disciplines", db_table="la_df_disc_tech_rel")
    competencies = models.ManyToManyField(Competency, verbose_name="Компетенции", blank=True, related_name="disciplines", db_table="la_df_disc_comp_rel")

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Дисциплина"
        verbose_name_plural = "Дисциплины"
        db_table = "la_df_discipline"


# Модель Vacancy представляет вакансию
class Vacancy(models.Model):
    """
    Модель Vacancy представляет вакансию

    Attributes:
        employer (ForeignKey): Внешний ключ на модель Employer. Связывает вакансию с работодателем.
        title (CharField): Название вакансии. Максимальная длина - 255 символов.
        description (TextField): Описание вакансии, её предметной области и сферы деятельности в целом.
        requirements (TextField): Требования к кандидату.
        responsibilities (TextField): Обязанности сотрудника.
        created_at (DateTimeField): Дата и время появления первичного упоминания вакансии.
        updated_at (DateTimeField): Дата и время последней редакции информации о вакансии.
        salary_min (DecimalField): Минимальная зарплата по вакансии.
        salary_max (DecimalField): Максимальная зарплата по вакансии.
        is_active (BooleanField): Активна ли вакансия.
        location (CharField): Местоположение работы.
        employment_type (CharField): Тип занятости (полная/частичная/удаленная).
    """

    EMPLOYMENT_CHOICES = [
        ('FULL', 'Полная занятость'),
        ('PART', 'Частичная занятость'),
        ('REMOTE', 'Удаленная работа'),
    ]

    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="vacancies", verbose_name="Работодатель")
    title = models.CharField(max_length=255, verbose_name="Название вакансии")
    description = models.TextField(verbose_name="Описание вакансии")
    requirements = models.TextField(verbose_name="Требования", blank=True)
    responsibilities = models.TextField(verbose_name="Обязанности", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Минимальная зарплата", null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Максимальная зарплата", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    location = models.CharField(max_length=255, verbose_name="Местоположение", blank=True)
    employment_type = models.CharField(max_length=10, choices=EMPLOYMENT_CHOICES, default='FULL', verbose_name="Тип занятости")
    technologies = models.ManyToManyField(Technology, verbose_name="Технологии", blank=True, related_name="vacancies", db_table="la_df_vacancy_tech_rel")
    competencies = models.ManyToManyField(Competency, verbose_name="Компетенции", blank=True, related_name="vacancies", db_table="la_df_vacancy_comp_rel")

    def __str__(self):
        return f"{self.title} ({self.employer.company_name})"
    
    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"
        db_table = "la_df_vacancy"

    def clean(self):
        if self.salary_max and self.salary_min and self.salary_max < self.salary_min:
            raise ValidationError("Максимальная зарплата не может быть меньше минимальной")


# Модель матрицы академических компетенций
class ACM(models.Model):
    """
    Модель AcademicCompetenceMatrix - модель, представляющая матрицу академических компетенций, на основании
    которой в дальнейшем будет формироваться основной вектор индивидуальной траектории обучения.

    Attributes:
        speciality (ForeignKey): Внешний ключ, связывающий матрицу с моделью специальности
        discipline_list  (JSONField): Перечень осваиваемых дисциплин (хранит указатели на дисциплины)
        technology_stack  (JSONField): Изучаемый стек технологий (подразумевается дублирование для дальнейшего приоритета и распределения)
    """


    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        verbose_name="Специальность",
        blank = True,
        null = True)  
    discipline_list = models.JSONField(verbose_name="Перечень изучаемых дисциплин")
    technology_stack  = models.JSONField(verbose_name="Перечень изучаемых технологий в течение времени")

    def __str__(self):
        return f"Матрица академических компетенций для {self.speciality}"

    class Meta:
        verbose_name = "Матрица академических компетенций"
        verbose_name_plural = "Матрицы академических компетенций"
        db_table = "la_df_academic_competence_matrix"
        

# Модель компетентностного профиля вакансии
class VCM(models.Model):
    """
    Модель CompetencyProfileOfVacancy - модель, представляющая компетентностный профиль вакансии.

    Attributes:
        vacancy (ForeignKey): Внешний ключ на модель Vacancy.
        technologies (ManyToManyField): Связь с моделью Technology.
        competencies (ManyToManyField): Связь с моделью Competency.
        description (TextField): Описание профиля компетенций. Максимальная длина - 400 символов.
    """

    vacancy = models.ForeignKey(
        Vacancy, 
        on_delete=models.CASCADE,
        verbose_name="Вакансия",
        related_name="vcm_profiles")
    technologies = models.ManyToManyField(
        Technology, 
        verbose_name="Технологии", 
        blank=True, 
        related_name="vcm_profiles", 
        db_table="la_df_vcm_tech_rel"
    )
    competencies = models.ManyToManyField(
        Competency, 
        verbose_name="Компетенции", 
        blank=True, 
        related_name="vcm_profiles", 
        db_table="la_df_vcm_comp_rel"
    )
    description = models.TextField(max_length=400, verbose_name="Описание профиля компетенций", blank=True)

    def __str__(self):
        return f"Профиль компетенций для вакансии: {self.vacancy}"

    class Meta:
        verbose_name = "Компетентностный профиль вакансии"
        verbose_name_plural = "Компетентностные профили вакансии"
        db_table = "la_df_competency_profile_of_vacancy"

class UCM(models.Model):
    """
    Модель UserCompetencyMatrix - модель, представляющая матрицу компетенций пользователя.

    Attributes:
        user_id (PositiveSmallIntegerField): ID пользователя.
        competencies_stack (JSONField): Перечень имеющихся компетенций.
        technology_stack (JSONField): Стек изучаемых технологий.
    """

    user_id = models.PositiveSmallIntegerField(verbose_name="ID пользователя")
    competencies_stack = models.JSONField(verbose_name="Перечень имеющихся компетенций")
    technology_stack = models.JSONField(verbose_name="Стек изучаемых технологий")

    def __str__(self):
        return f"Матрица компетенций пользователя {self.user}"
    
    class Meta:
        verbose_name = "Матрица компетенций пользователя"
        verbose_name_plural = "Матрицы компетенций пользователей"
        db_table = "la_df_user_competency_matrix"
