from django.db import models
from django.conf import settings

from src.modules.project_ed.models import Project


class ProjectNotification(models.Model):
    """Уведомление в рамках модуля управления проектами (ProjectEd).

    Используется для доставки событий пользователям, связанным с проектом
    (руководитель, куратор, заказчик, исполнитель и т.д.).
    """

    class NotificationType(models.TextChoices):
        INFO = 'info', 'Информация'
        WARNING = 'warning', 'Предупреждение'
        SUCCESS = 'success', 'Успех'
        ERROR = 'error', 'Ошибка'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Проект',
    )

    # Получатель уведомления. Может быть NULL для системных/широковещательных записей
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_ed_notifications',
        verbose_name='Получатель',
    )

    # Инициатор события (кто спровоцировал уведомление)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_ed_notifications_as_actor',
        verbose_name='Инициатор',
    )

    type = models.CharField('Тип', max_length=32, choices=NotificationType.choices, default=NotificationType.INFO)
    title = models.CharField('Заголовок', max_length=255)
    message = models.TextField('Сообщение', blank=True, default='')

    # Произвольные данные для фронтенда (например, действия, ссылки, параметры)
    payload = models.JSONField('Данные', default=dict, blank=True)

    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Дата прочтения', null=True, blank=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Уведомление проекта'
        verbose_name_plural = 'Уведомления проекта'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self) -> str:
        base = self.title or 'Уведомление'
        return f"[{self.get_type_display()}] {base} (project={self.project_id})"

    def mark_read(self):
        """Отметить уведомление как прочитанное с установкой времени."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
