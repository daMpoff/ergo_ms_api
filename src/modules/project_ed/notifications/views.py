from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.project_ed.notifications.models import ProjectNotification
from src.modules.project_ed.notifications.serializers import ProjectNotificationSerializer


class ProjectNotificationViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = ProjectNotification.objects.select_related('project', 'recipient', 'actor')
    serializer_class = ProjectNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.get_safe_user()
        base = self.get_safe_queryset(super().get_queryset())
        if user is None:
            return base.none()
        # Только уведомления текущего пользователя
        return base.filter(recipient=user)

    def perform_create(self, serializer):
        # actor = текущий пользователь; recipient и project должны быть в данных
        serializer.save(actor=getattr(self.request, 'user', None))

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        user = self.get_safe_user()
        if user is None:
            return Response({'count': 0})
        count = ProjectNotification.objects.filter(recipient=user, is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        if notif.recipient_id != getattr(request.user, 'id', None):
            return Response({'detail': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        notif.mark_read()
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        user = self.get_safe_user()
        if user is None:
            return Response({'updated': 0})
        from django.utils import timezone
        updated = ProjectNotification.objects.filter(recipient=user, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'updated': updated})
