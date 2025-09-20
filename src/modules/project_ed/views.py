from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.project_ed.models import Project, Category, Subcategory, TargetIndicator
from src.modules.project_ed.serializers import (
    ProjectSerializer, 
    CategorySerializer, 
    CategoryCreateUpdateSerializer,
    SubcategorySerializer,
    TargetIndicatorSerializer
)


class ProjectPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner_id == getattr(request.user, 'id', None)
        return obj.owner_id == getattr(request.user, 'id', None)


class ProjectViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = ProjectPagination

    def get_queryset(self):
        base_qs = super().get_queryset()
        user = self.get_safe_user()
        if user is None:
            return self.get_safe_queryset(base_qs)
        return base_qs.filter(owner=user)


class CategoryViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления категориями показателей."""
    queryset = Category.objects.filter(is_active=True).prefetch_related('subcategories')
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CategoryCreateUpdateSerializer
        return CategorySerializer
    
    def get_queryset(self):
        # Принудительно исправляем порядок категорий при загрузке
        categories = Category.objects.filter(is_active=True).order_by('order')
        for i, category in enumerate(categories):
            if category.order != i:
                category.order = i
                category.save()
        
        return Category.objects.filter(is_active=True).prefetch_related('subcategories')
    
    @action(detail=True, methods=['get'])
    def subcategories(self, request, pk=None):
        """Получить подкатегории для конкретной категории."""
        category = self.get_object()
        subcategories = category.subcategories.filter(is_active=True)
        serializer = SubcategorySerializer(subcategories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def safe_delete(self, request, pk=None):
        """Безопасное удаление категории с проверкой использования."""
        category = self.get_object()
        
        # Проверяем, используется ли категория в целевых показателях
        indicators_count = category.indicators_count
        
        if indicators_count > 0:
            return Response({
                'error': 'Категория не может быть удалена',
                'message': f'Категория используется {indicators_count} целевыми показателями',
                'indicators_count': indicators_count
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Если не используется, помечаем как неактивную
        category.is_active = False
        category.save()
        
        return Response({'message': 'Категория успешно удалена'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'])
    def update_order(self, request, pk=None):
        """Обновление порядка категории с автоматическим пересчетом порядка других категорий."""
        category = self.get_object()
        new_order = request.data.get('order')
        
        if new_order is None:
            return Response({
                'error': 'Поле order обязательно'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_order = int(new_order)
        except (ValueError, TypeError):
            return Response({
                'error': 'Поле order должно быть числом'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем все категории, отсортированные по порядку
        all_categories = list(Category.objects.filter(is_active=True).order_by('order'))
        
        # Находим текущий индекс категории в отсортированном списке
        current_index = next((i for i, cat in enumerate(all_categories) if cat.id == category.id), -1)
        
        if current_index == -1:
            return Response({
                'error': 'Категория не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Если порядок не изменился, ничего не делаем
        if current_index == new_order:
            return Response({'message': 'Порядок не изменился'}, status=status.HTTP_200_OK)
        
        # Создаем новый список с обновленными порядками
        updated_categories = []
        
        # Создаем новый список категорий без текущей
        other_categories = [cat for cat in all_categories if cat.id != category.id]
        
        # Вставляем текущую категорию на новую позицию
        if new_order == 0:
            # Вставляем в начало
            updated_categories.append(category)
            updated_categories.extend(other_categories)
        elif new_order >= len(other_categories):
            # Вставляем в конец
            updated_categories.extend(other_categories)
            updated_categories.append(category)
        else:
            # Вставляем в середину
            updated_categories.extend(other_categories[:new_order])
            updated_categories.append(category)
            updated_categories.extend(other_categories[new_order:])
        
        # Устанавливаем правильные порядки для всех категорий
        for i, cat in enumerate(updated_categories):
            cat.order = i
        
        # Сохраняем все изменения
        for cat in updated_categories:
            cat.save()
        
        return Response({
            'message': 'Порядок категории успешно обновлен',
            'old_order': current_index,
            'new_order': new_order
        }, status=status.HTTP_200_OK)


class SubcategoryViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления подкатегориями показателей."""
    queryset = Subcategory.objects.filter(is_active=True)
    serializer_class = SubcategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        queryset = Subcategory.objects.filter(is_active=True)
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset
    
    @action(detail=True, methods=['delete'])
    def safe_delete(self, request, pk=None):
        """Безопасное удаление подкатегории с проверкой использования."""
        subcategory = self.get_object()
        
        # Проверяем, используется ли подкатегория в целевых показателях
        indicators_count = subcategory.indicators_count
        
        if indicators_count > 0:
            return Response({
                'error': 'Подкатегория не может быть удалена',
                'message': f'Подкатегория используется {indicators_count} целевыми показателями',
                'indicators_count': indicators_count
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Если не используется, помечаем как неактивную
        subcategory.is_active = False
        subcategory.save()
        
        return Response({'message': 'Подкатегория успешно удалена'}, status=status.HTTP_200_OK)


class TargetIndicatorViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления целевыми показателями."""
    queryset = TargetIndicator.objects.filter(is_active=True)
    serializer_class = TargetIndicatorSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        category_id = self.request.query_params.get('category_id')
        subcategory_id = self.request.query_params.get('subcategory_id')
        
        queryset = TargetIndicator.objects.filter(is_active=True)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)
        
        return queryset
    
    def perform_create(self, serializer):
        # Автоматически устанавливаем проект из контекста
        project_id = self.request.data.get('project_id')
        if project_id:
            serializer.save(project_id=project_id)
        else:
            serializer.save()