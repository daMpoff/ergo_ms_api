from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.project_ed.notifications.models import ProjectNotification, ProjectNotificationDelivery
from src.modules.project_ed.notifications.serializers import (
    ProjectNotificationDeliverySerializer,
    ProjectNotificationCreateSerializer,
)


class ProjectNotificationViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = ProjectNotificationDelivery.objects.select_related('notification__project', 'notification__actor', 'recipient')
    serializer_class = ProjectNotificationDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.get_safe_user()
        base = self.get_safe_queryset(super().get_queryset())
        if user is None:
            return base.none()
        # Только доставки текущего пользователя
        return base.filter(recipient=user)

    def perform_create(self, serializer):
        # Создание самой сущности уведомления
        create_serializer = ProjectNotificationCreateSerializer(data=self.request.data)
        create_serializer.is_valid(raise_exception=True)
        notification = create_serializer.save(actor=getattr(self.request, 'user', None))
        # Создание доставки текущему пользователю по умолчанию
        delivery = ProjectNotificationDelivery.objects.create(
            notification=notification,
            recipient=getattr(self.request, 'user', None),
        )
        # Возвращаем как доставку
        serializer.instance = delivery

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        user = self.get_safe_user()
        if user is None:
            return Response({'count': 0})
        count = ProjectNotificationDelivery.objects.filter(recipient=user, is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        delivery = self.get_object()
        if delivery.recipient_id != getattr(request.user, 'id', None):
            return Response({'detail': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        delivery.mark_read()
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        user = self.get_safe_user()
        if user is None:
            return Response({'updated': 0})
        from django.utils import timezone
        updated = ProjectNotificationDelivery.objects.filter(recipient=user, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'updated': updated})
