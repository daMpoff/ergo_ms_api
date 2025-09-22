from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.utils import ProgrammingError, OperationalError, DatabaseError
from django.conf import settings

from .models import UserProfile, Role


@receiver(post_save, sender=User)
def create_project_ed_user_profile(sender, instance, created, **kwargs):
    """Создать профиль пользователя ProjectEd при создании нового пользователя.
    
    Автоматически назначает роль 'Пользователь' новым пользователям.
    """
    if created:
        # Безопасно пропускаем, если таблицы ещё нет (например, модуль не мигрирован)
        try:
            # Проверяем, существует ли уже профиль ProjectEd для этого пользователя
            profile, profile_created = UserProfile.objects.get_or_create(user=instance)
            
            if profile_created:
                # Получаем или создаем роль "Пользователь"
                user_role, role_created = Role.objects.get_or_create(
                    name='Пользователь',
                    defaults={'name': 'Пользователь'}
                )
                
                # Назначаем роль пользователю
                profile.role_ref = user_role
                profile.save()
                
                # Логируем создание профиля (опционально)
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'Создан профиль ProjectEd для пользователя {instance.username} с ролью "Пользователь"')
                
        except (ProgrammingError, OperationalError, DatabaseError) as e:
            # Модуль ProjectEd может быть отключен или не мигрирован
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f'Модуль ProjectEd недоступен: {e}')
            pass
