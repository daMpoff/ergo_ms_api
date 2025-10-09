from django.db import models
from django.conf import settings

from src.modules.project_ed.models import Project


class ProjectNotification(models.Model):
    """Уведомление в рамках модуля управления проектами (ProjectEd).

    Сущность события без привязки к конкретному получателю.
    Доставка до пользователей реализована через ProjectNotificationDelivery.
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

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Уведомление проекта'
        verbose_name_plural = 'Уведомления проекта'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self) -> str:
        base = self.title or 'Уведомление'
        return f"[{self.get_type_display()}] {base} (project={self.project_id})"


class ProjectNotificationDelivery(models.Model):
    """Доставка уведомления конкретному пользователю с индивидуальным статусом чтения."""
    notification = models.ForeignKey(
        ProjectNotification,
        on_delete=models.CASCADE,
        related_name='deliveries',
        verbose_name='Уведомление',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_ed_notification_deliveries',
        verbose_name='Получатель',
    )

    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Дата прочтения', null=True, blank=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Доставка уведомления'
        verbose_name_plural = 'Доставки уведомлений'
        unique_together = (('notification', 'recipient'),)
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['notification']),
        ]

    def mark_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
