from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q


class BaseLMSViewSet(viewsets.ModelViewSet):
    """Базовый ViewSet для LMS с общими настройками"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]


class UserOwnedViewSet(BaseLMSViewSet):
    """ViewSet для объектов, принадлежащих пользователю"""
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class SubjectRelatedViewSet(BaseLMSViewSet):
    """ViewSet для объектов, связанных с курсами (с проверкой доступа)"""
    
    def get_queryset(self):
        user = self.request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return self.queryset.all()
        elif 'teacher' in user_roles or hasattr(user, 'teacher'):
            # Преподаватели видят свои курсы + опубликованные
            return self.queryset.filter(
                Q(subject__teacher=user) | Q(subject__is_published=True)
            ).distinct()
        else:
            # Студенты видят только опубликованные курсы
            return self.queryset.filter(subject__is_published=True)


class ReadOnlyLMSViewSet(viewsets.ReadOnlyModelViewSet):
    """Базовый ReadOnly ViewSet для LMS"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]


class ToggleVisibilityMixin:
    """Миксин для переключения видимости объектов"""
    
    @action(detail=True, methods=['patch'])
    def toggle_visibility(self, request, pk=None):
        """Переключить видимость объекта"""
        obj = self.get_object()
        obj.is_visible = not obj.is_visible
        obj.save()
        return Response({
            'message': f'Видимость {"включена" if obj.is_visible else "отключена"}',
            'is_visible': obj.is_visible
        })


class OrderingMixin:
    """Миксин для упорядочивания объектов"""
    
    @action(detail=True, methods=['patch'])
    def update_order(self, request, pk=None):
        """Обновить порядок объекта"""
        obj = self.get_object()
        new_order = request.data.get('sort_order')
        
        if new_order is not None:
            obj.sort_order = new_order
            obj.save()
            return Response({'message': 'Порядок обновлен', 'sort_order': obj.sort_order})
        
        return Response({'error': 'Не указан sort_order'}, status=status.HTTP_400_BAD_REQUEST) 