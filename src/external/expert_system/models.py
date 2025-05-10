from django.db import models
from django.contrib.auth.models import User

class ExpertSystemStudyGroup(models.Model):
    """
    Учебная группа (например: О-22-ИАС).
    Хранит название группы, чтобы привязать студента к его потоку.
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
    Расширение User для студентов.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="Пользователь-студент"
    )
    first_name = models.CharField("Имя", max_length=150)
    last_name = models.CharField("Фамилия", max_length=150)
    study_group = models.ForeignKey(
        ExpertSystemStudyGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Учебная группа"
    )
    has_experience = models.BooleanField("Есть опыт в IT", default=False)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"