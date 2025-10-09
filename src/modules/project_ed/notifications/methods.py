from django.contrib.auth import get_user_model
from src.modules.project_ed.models import Project
from .models import ProjectNotification, ProjectNotificationDelivery

User = get_user_model()


def get_expert_group_users():
    """Получить всех пользователей с ролью 'Экспертная группа'."""
    return User.objects.filter(
        project_ed_profile__role_ref__name='Экспертная группа'
    ).select_related('project_ed_profile__role_ref')


def create_project_submission_notification(project: Project, actor: User):
    """Создать уведомление о отправке проекта на рассмотрение для группы экспертов.

    Возвращает кортеж: (notification, deliveries_list)
    """
    expert_users = list(get_expert_group_users())

    if not expert_users:
        return None, []

    notification = ProjectNotification.objects.create(
        project=project,
        actor=actor,
        type=ProjectNotification.NotificationType.INFO,
        title='Новый проект отправлен на рассмотрение',
        message=f'Проект "{project.short_name}" отправлен на рассмотрение экспертной группе руководителем {actor.get_full_name() or actor.username}.',
        payload={
            'project_id': project.id,
            'project_name': project.short_name,
            'actor_id': actor.id,
            'actor_name': actor.get_full_name() or actor.username,
            'action': 'project_submitted_for_review'
        }
    )

    deliveries = [
        ProjectNotificationDelivery(
            notification=notification,
            recipient=expert,
        ) for expert in expert_users
    ]
    ProjectNotificationDelivery.objects.bulk_create(deliveries, ignore_conflicts=True)

    return notification, deliveries