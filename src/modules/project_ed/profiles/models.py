from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    """Профиль пользователя для модуля ProjectEd.
    
    Объединяет основную информацию о пользователе (роль, должность, факультет, кафедра)
    с расширенными настройками профиля (биография, контакты, приватность).
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_ed_profile',
        verbose_name='Пользователь'
    )
    
    # Ссылочные поля на справочники (основная информация)
    role_ref = models.ForeignKey(
        'project_ed.Role', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profiles', verbose_name='Роль (справочник)'
    )
    position_ref = models.ForeignKey(
        'project_ed.Position', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profiles', verbose_name='Должность (справочник)'
    )
    faculty_ref = models.ForeignKey(
        'project_ed.Faculty', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profiles', verbose_name='Факультет (справочник)'
    )
    department_ref = models.ForeignKey(
        'project_ed.Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profiles', verbose_name='Кафедра (справочник)'
    )
    
    # Настройки приватности
    is_public = models.BooleanField('Публичный профиль', default=True)
    show_email = models.BooleanField('Показывать email', default=False)
       
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
        ordering = ['user__first_name', 'user__last_name']
    
    def __str__(self):
        return f"Профиль {self.user.get_full_name() or self.user.username}"
    
    @property
    def role_name(self):
        """Название роли."""
        return self.role_ref.name if self.role_ref else None
    
    @property
    def position_name(self):
        """Название должности."""
        return self.position_ref.name if self.position_ref else None
    
    @property
    def faculty_name(self):
        """Название факультета."""
        return self.faculty_ref.name if self.faculty_ref else None
    
    @property
    def department_name(self):
        """Название кафедры."""
        return self.department_ref.name if self.department_ref else None
