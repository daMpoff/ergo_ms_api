from django.db import models

class Speciality(models.Model):
    """
    Модель Speciality представляет собой информацию о специальности (направлении подготовки).

    Attributes:
        code (CharField): Код специальности. Максимальная длина — 20 символов.
        name (CharField): Наименование специальности. Максимальная длина — 255 символов.
        specialization (CharField): Наименование специализации. Максимальная длина - 255 символов.
        department (CharField): Кафедра, выпускающая специальность. Максимальная длина - 255 символов.
        faculty (CharField): Факультет. Максимальная длина - 255 символов.
        education_duration (PositiveIntegerField): Срок получения образования. Подразумевается измерение в количестве месяцев. 
        year_of_admission (PositiveIntegerField): Год поступления (для учета различий в УП)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="Код специальности")
    name = models.CharField(max_length=255, verbose_name="Специальность")
    specialization = models.CharField(max_length=255, verbose_name="Специализация")
    department = models.CharField(max_length=255, verbose_name="Кафедра")
    faculty = models.CharField(max_length=255, verbose_name="Факультет")
    education_duration = models.PositiveIntegerField(verbose_name="Срок получения образования")
    year_of_admission = models.CharField(max_length=4, verbose_name="Год поступления")

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Специальность"
        verbose_name_plural = "Специальности"