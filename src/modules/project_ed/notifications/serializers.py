from rest_framework import serializers

from src.modules.project_ed.notifications.models import ProjectNotification


class ProjectNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectNotification
        fields = [
            'id',
            'project',
            'recipient',
            'actor',
            'type',
            'title',
            'message',
            'payload',
            'is_read',
            'read_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['actor', 'read_at', 'created_at', 'updated_at']

from rest_framework import serializers

# Создавайте свои сериализаторы здесь