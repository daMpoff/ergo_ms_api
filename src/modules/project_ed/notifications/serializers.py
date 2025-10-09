from rest_framework import serializers

from src.modules.project_ed.notifications.models import (
    ProjectNotification,
    ProjectNotificationDelivery,
)


class ProjectNotificationDeliverySerializer(serializers.ModelSerializer):
    """Сериализатор доставки: отдаёт плоско данные уведомления + состояние чтения."""

    # Пробрасываем поля из уведомления
    project = serializers.PrimaryKeyRelatedField(read_only=True, source='notification.project')
    actor = serializers.PrimaryKeyRelatedField(read_only=True, source='notification.actor')
    type = serializers.CharField(read_only=True, source='notification.type')
    title = serializers.CharField(read_only=True, source='notification.title')
    message = serializers.CharField(read_only=True, source='notification.message')
    payload = serializers.JSONField(read_only=True, source='notification.payload')
    created_at = serializers.DateTimeField(read_only=True, source='notification.created_at')
    updated_at = serializers.DateTimeField(read_only=True, source='notification.updated_at')

    class Meta:
        model = ProjectNotificationDelivery
        fields = [
            'id',                 # id доставки
            'project',
            'actor',
            'type',
            'title',
            'message',
            'payload',
            'is_read',            # состояние чтения этой доставки
            'read_at',
            'created_at',         # дата создания уведомления
            'updated_at',
        ]
        read_only_fields = fields


class ProjectNotificationCreateSerializer(serializers.ModelSerializer):
    """Создание уведомления: принимает project, actor задаётся из request, без recipient.
    Получателей создаём отдельно (bulk) во вью/методах.
    """

    class Meta:
        model = ProjectNotification
        fields = [
            'id',
            'project',
            'type',
            'title',
            'message',
            'payload',
        ]
        read_only_fields = ['id']