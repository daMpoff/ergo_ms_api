from django.db import models


# Модель Employer представляет работодателя
class Employer(models.Model):
    """
    Модель Employer представляет работодателя

    Attributes:
        company_name (CharField): Название компании (работодателя). Максимальная длина - 255 символов.
        description (TextField): Описание компании, её предметной области и сферы деятельности в целом.
        email (EmailField): Электронная почта компании для связи.
        created_at (DateTimeField): Дата и время появления первичного упоминания работодателя.
        updated_at (DateTimeField): Дата и время последней редакции информации о работодателе.
        rating (DecimalField): Рейтинг работодателя от 1 до 5. Вещественное число с ограничением в два знака после запятой.
    """

    company_name = models.CharField(max_length=255, verbose_name="Название компании")
    description = models.TextField(verbose_name="Описание компании")
    email = models.EmailField(verbose_name="Контактный email", unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="дата создания записи")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    rating = models.DecimalField(max_digits=3, decimal_places=2)

    def __str__(self):
        return f"{self.company_name}"
    
    class Meta:
        verbose_name = "Работодатель"
        verbose_name_plural = "Работодатели"
        db_table = "la_employer"
