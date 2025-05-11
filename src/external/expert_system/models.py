from django.db import models
from django.contrib.auth.models import User

class ExpertSystemStudyGroup(models.Model):
    """
    Учебная группа (например: О-22-ИАС, 0-21-ПРИ).
    Используется для привязки студента к его потоку.
    """
    name = models.CharField(
        verbose_name="Название группы",
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.name
    
class ExpertSystemStudentProfile(models.Model):
    """
    Расширение стандартного User для студентов.
    Хранит имя, фамилию, группу обучения и флаг опыта.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="Пользователь-студент"
    )
    first_name = models.CharField(
        verbose_name="Имя",
        max_length=150
    )
    last_name = models.CharField(
        verbose_name="Фамилия",
        max_length=150
    )
    study_group = models.ForeignKey(
        ExpertSystemStudyGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Учебная группа"
    )
    has_experience = models.BooleanField(
        verbose_name="Есть опыт в IT",
        default=False
    )

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

class ExpertsystemCompanyProfile(models.Model):
    """
    Расширение User для работодателей/компаний.
    Хранит данные о компании и контактном лице.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='company_profile',
        verbose_name="Пользователь-работодатель"
    )
    company_name = models.CharField(
        verbose_name="Название компании",
        max_length=200
    )
    description = models.TextField(
        verbose_name="Описание компании",
        blank=True
    )
    website = models.URLField(
        verbose_name="Веб-сайт",
        blank=True
    )
    contact_person = models.CharField(
        verbose_name="Контактное лицо",
        max_length=150
    )
    contact_email = models.EmailField(
        verbose_name="Контактный E-mail",
        blank=True
    )
    is_verified = models.BooleanField(
        verbose_name="Аккаунт подтверждён",
        default=False
    )

    def __str__(self):
        return self.company_name
    
class ExpertSystemSkill(models.Model):
    """
    Справочник навыков
    """
    name = models.CharField(
        verbose_name="Навык",
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.name
    
STATUS_CHOICES = [
    ('unconfirmed', 'Неподтверждён'),
    ('confirmed',   'Подтверждён'),
]

class ExpertSystemUserSkill(models.Model):
    """
    Связь «пользователь–навык» с полем статуса.
    Позволяет хранить, какие навыки указал пользователь
    и прошёл ли он по ним тест.
    """
    user = models.ForeignKey(
        ExpertSystemStudentProfile,
        on_delete=models.CASCADE,
        related_name='user_skills',
        verbose_name="Пользователь"
    )
    skill = models.ForeignKey(
        ExpertSystemSkill,
        on_delete=models.CASCADE,
        related_name='user_skills',
        verbose_name="Навык"
    )
    status = models.CharField(
        verbose_name="Статус навыка",
        max_length=20,
        choices=STATUS_CHOICES,
        default='unconfirmed'
    )

    class Meta:
        unique_together = ('user', 'skill')
        verbose_name = "Навык пользователя"
        verbose_name_plural = "Навыки пользователей"

    def __str__(self):
        return f"{self.user.username} — {self.skill.name} ({self.status})"
    
class ExpertSystemRole(models.Model):
    """
    Список целевых ролей/профессий
    (Разработчик, дизайнер и т.п.)
    """
    name = models.CharField(
        verbose_name="Роль",
        max_length=100,
        unique=True
    )
    description = models.TextField(
        verbose_name="Описание роли"
    )

    def __str__(self):
        return self.name
    
class ExpertSystemTrajectoryStep(models.Model):
    """
    Шаг плана обучения для конкретной роли.
    order задаёт порядок отображения.
    """
    role = models.ForeignKey(
        ExpertSystemRole,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name="Роль"
    )
    order = models.PositiveIntegerField(
        verbose_name="Порядок шага"
    )
    description = models.TextField(
        verbose_name="Описание шага"
    )

    class Meta:
        ordering = ['order']
        verbose_name = "Шаг траектории"
        verbose_name_plural = "Шаги траектории"

    def __str__(self):
        return f"{self.role.name} — шаг {self.order}"


class ExpertSystemOrientationTest(models.Model):
    """
    Профориентационный тест.
    Содержит лишь название — вопросы и ответы
    хранятся в связанных моделях.
    """
    name = models.CharField(
        verbose_name="Название теста",
        max_length=200
    )

    def __str__(self):
        return self.name


class ExpertSystemOrientationQuestion(models.Model):
    """
    Вопрос профориентационного теста.
    Привязан к конкретному OrientationTest.
    """
    test = models.ForeignKey(
        ExpertSystemOrientationTest,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Тест"
    )
    text = models.TextField(
        verbose_name="Текст вопроса"
    )

    def __str__(self):
        return f"{self.test.name} — вопрос {self.id}"


class ExpertSystemOrientationAnswer(models.Model):
    """
    Вариант ответа в профориентационном тесте.
    Каждый ответ даёт вес именно к указанной роли.
    """
    question = models.ForeignKey(
        ExpertSystemOrientationQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name="Вопрос"
    )
    text = models.CharField(
        verbose_name="Текст ответа",
        max_length=200
    )
    weight = models.IntegerField(
        verbose_name="Вес ответа",
        default=0
    )
    role = models.ForeignKey(
        ExpertSystemRole,
        on_delete=models.CASCADE,
        verbose_name="Роль для начисления баллов"
    )

    def __str__(self):
        return f"{self.text} (+{self.weight} к {self.role.name})"


class ExpertSystemTest(models.Model):
    """
    Модель теста для проверки навыков опытных пользователей.
    Привязан к конкретному Skill.
    """
    skill = models.ForeignKey(
        ExpertSystemSkill,
        on_delete=models.CASCADE,
        related_name='tests',
        verbose_name="Навык"
    )
    name = models.CharField(
        verbose_name="Название теста",
        max_length=200
    )

    def __str__(self):
        return f"{self.name} ({self.skill.name})"


class ExpertSystemQuestion(models.Model):
    """
    Вопрос внутри теста навыка.
    """
    test = models.ForeignKey(
        ExpertSystemTest,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Тест"
    )
    text = models.TextField(
        verbose_name="Текст вопроса"
    )

    def __str__(self):
        return f"{self.test.name} — вопрос {self.id}"


class ExpertSystemAnswer(models.Model):
    """
    Вариант ответа на вопрос теста навыка.
    is_correct=True для правильного варианта.
    """
    question = models.ForeignKey(
        ExpertSystemQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name="Вопрос"
    )
    text = models.CharField(
        verbose_name="Текст ответа",
        max_length=200
    )
    is_correct = models.BooleanField(
        verbose_name="Правильный ответ",
        default=False
    )

    def __str__(self):
        return f"{self.text} ({'✓' if self.is_correct else '✗'})"


class ExpertSystemTestResult(models.Model):
    """
    Результат прохождения теста навыка пользователем.
    Хранит итоговый балл и статус passed.
    """
    user = models.ForeignKey(
        ExpertSystemStudentProfile,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    test = models.ForeignKey(
        ExpertSystemTest,
        on_delete=models.CASCADE,
        verbose_name="Тест"
    )
    score = models.FloatField(
        verbose_name="Баллы"
    )
    passed = models.BooleanField(
        verbose_name="Пройдено",
        default=False
    )

    class Meta:
        verbose_name = "Результат теста"
        verbose_name_plural = "Результаты тестов"

    def __str__(self):
        return f"{self.user.username} — {self.test.name}: {self.score}"


class ExpertSystemVacancy(models.Model):
    """
    Вакансия, создаётся работодателем.
    Содержит заголовок, описание и требуемые навыки.
    """
    employer = models.ForeignKey(
        ExpertsystemCompanyProfile,
        on_delete=models.CASCADE,
        related_name='vacancies',
        verbose_name="Работодатель"
    )
    title = models.CharField(
        verbose_name="Заголовок вакансии",
        max_length=200
    )
    description = models.TextField(
        verbose_name="Описание вакансии"
    )
    required_skills = models.ManyToManyField(
        ExpertSystemSkill,
        through='ExpertSystemVacancySkill',
        related_name='vacancies',
        verbose_name="Требуемые навыки"
    )

    def __str__(self):
        return self.title


class ExpertSystemVacancySkill(models.Model):
    """
    Промежуточная модель «Вакансия–Навык».
    Помечает, является ли навык обязательным.
    """
    vacancy = models.ForeignKey(
        ExpertSystemVacancy,
        on_delete=models.CASCADE,
        verbose_name="Вакансия"
    )
    skill = models.ForeignKey(
        ExpertSystemSkill,
        on_delete=models.CASCADE,
        verbose_name="Навык"
    )
    is_mandatory = models.BooleanField(
        verbose_name="Обязательный навык",
        default=True
    )

    class Meta:
        unique_together = ('vacancy', 'skill')
        verbose_name = "Навык вакансии"
        verbose_name_plural = "Навыки вакансии"

    def __str__(self):
        return f"{self.vacancy.title} — {self.skill.name}"


class ExpertSystemCandidateApplication(models.Model):
    """
    Заявка кандидата на вакансию.
    Хранит дату подачи и рассчитанный match_score.
    """
    vacancy = models.ForeignKey(
        ExpertSystemVacancy,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Вакансия"
    )
    candidate = models.ForeignKey(
        ExpertSystemStudentProfile,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Кандидат"
    )
    applied_at = models.DateTimeField(
        verbose_name="Дата подачи заявки",
        auto_now_add=True
    )
    match_score = models.FloatField(
        verbose_name="Коэффициент совпадения",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Заявка кандидата"
        verbose_name_plural = "Заявки кандидатов"

    def __str__(self):
        return f"{self.candidate.username} на «{self.vacancy.title}»"
    

class ExpertSystemOrientationTestResult(models.Model):
    """
    Итог профориентационного теста для пользователя:
    привязка к тесту, время запуска и рекомендованная роль.
    """
    user = models.ForeignKey(
        ExpertSystemStudentProfile,
        on_delete=models.CASCADE,
        related_name='orientation_results',
        verbose_name="Пользователь"
    )
    test = models.ForeignKey(
        ExpertSystemOrientationTest,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name="Тест"
    )
    taken_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата прохождения")
    # Можно хранить сразу лучшую роль и процент
    best_role = models.ForeignKey(
        ExpertSystemRole,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Рекомендуемая роль"
    )
    best_score = models.FloatField(
        verbose_name="Процент соответствия",
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.user} — {self.test.name} ({self.best_role}: {self.best_score}%)"


class ExpertSystemOrientationUserAnswer(models.Model):
    """
    Ответ студента на конкретный вопрос ориентационного теста.
    Позволяет в любой момент пересчитать баллы, посмотреть историю ответов.
    """
    result = models.ForeignKey(
        ExpertSystemOrientationTestResult,
        on_delete=models.CASCADE,
        related_name='user_answers',
        verbose_name="Результат теста"
    )
    question = models.ForeignKey(
        ExpertSystemOrientationQuestion,
        on_delete=models.CASCADE,
        verbose_name="Вопрос"
    )
    answer = models.ForeignKey(
        ExpertSystemOrientationAnswer,
        on_delete=models.CASCADE,
        verbose_name="Выбранный ответ"
    )

    class Meta:
        unique_together = ('result', 'question')
        verbose_name = "Ответ на ориентационный вопрос"
        verbose_name_plural = "Ответы на ориентационные вопросы"

    def __str__(self):
        return f"{self.result.user} — {self.question.id} → {self.answer.text}"