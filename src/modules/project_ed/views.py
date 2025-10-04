from django.shortcuts import render
from django.db.models import Prefetch
from django.db import models as dj_models
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.project_ed.models import (
    Project, Category, Subcategory, TargetIndicator, EventBlock, Event,
    Role, Position, Faculty, Department
)
from src.modules.project_ed.serializers import (
    ProjectSerializer, 
    CategorySerializer, 
    CategoryCreateUpdateSerializer,
    SubcategorySerializer,
    TargetIndicatorSerializer,
    EventBlockSerializer,
    EventBlockCreateUpdateSerializer,
    EventSerializer,
    ProjectEdRoleSerializer,
    ProjectEdPositionSerializer,
    ProjectEdFacultySerializer,
    ProjectEdDepartmentSerializer
)
from src.modules.project_ed.projects.serializers import (
    ProjectCreateSerializer,
    ProjectReadSerializer,
    ProjectDetailSerializer,
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


class IsProjectEdAdmin(permissions.BasePermission):
    """Доступ только для пользователей с ролью 'Администратор' в ProjectEd.

    Проверяет связанный профиль `UserProfile` либо принадлежность пользователя к группе с именем 'Администратор'.
    """

    message = 'Доступ разрешен только администраторам ProjectEd.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        # Проверка через профиль ProjectEd (теперь в подмодуле profiles)
        try:
            profile = getattr(user, 'project_ed_profile', None)
            if profile and (
                getattr(getattr(profile, 'role_ref', None), 'name', None) == 'Администратор'
            ):
                return True
        except Exception:
            pass

        # Резервная проверка через группы Django
        try:
            if user.groups.filter(name='Администратор').exists():
                return True
        except Exception:
            pass

        return False


class ProjectViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Project.objects.select_related('owner', 'manager', 'curator', 'customer').prefetch_related(
        'user_roles__role',
        'executors__user__avatar',
        'executors__user__project_ed_profile',
        'budget_items__stage',
        'budget_totals',
        'tasks',
        'planned_results',
    )
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = ProjectPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        if self.action == 'list':
            return ProjectReadSerializer
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectSerializer

    def get_queryset(self):
        from django.db.models import Q
        
        base_qs = super().get_queryset()
        user = self.get_safe_user()
        if user is None:
            return self.get_safe_queryset(base_qs)
        
        # Получаем все проекты пользователя: где он владелец, руководитель, куратор, заказчик или исполнитель
        user_projects = base_qs.filter(
            Q(owner=user) |
            Q(manager=user) |
            Q(curator=user) |
            Q(customer=user) |
            Q(executors__user=user)
        ).distinct()
        
        return user_projects

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def public_view(self, request, pk=None):
        """
        Публичный просмотр проекта по ID для всех аутентифицированных пользователей.
        Позволяет просматривать чужие проекты.
        """
        try:
            project = self.get_object()
            serializer = ProjectDetailSerializer(project, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': 'Проект не найден'}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        """Переопределяем create, чтобы возвращать ProjectReadSerializer,
        а не входной ProjectCreateSerializer (во избежание ошибок сериализации DictField)."""
        serializer = ProjectCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        read_data = ProjectReadSerializer(project).data
        return Response(read_data, status=status.HTTP_201_CREATED)


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
        category_id = self.request.query_params.get('category_id')
        subcategory_id = self.request.query_params.get('subcategory_id')
        # Поддержка фильтрации по блоку мероприятий
        event_block_id = (
            self.request.query_params.get('event_block')
            or self.request.query_params.get('event_block_id')
            or self.request.query_params.get('block_id')
        )

        # Если задан event_block — считаем его приоритетным фильтром
        if event_block_id:
            return TargetIndicator.objects.filter(is_active=True, event_block_id=event_block_id)

        queryset = TargetIndicator.objects.filter(is_active=True)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()


class EventBlockViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления блоками мероприятий."""
    queryset = EventBlock.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            'events', 
            queryset=Event.objects.filter(is_active=True).prefetch_related(
                Prefetch('projects', queryset=Project.objects.select_related('owner'))
            )
        ),
        'subcategory'
    )
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EventBlockCreateUpdateSerializer
        return EventBlockSerializer
    
    def update(self, request, *args, **kwargs):
        """Переопределяем update для принудительного вызова save() модели."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Принудительно вызываем save() модели для обновления кодов мероприятий
        instance = serializer.save()
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    def get_queryset(self):
        # Принудительно исправляем порядок блоков при загрузке
        blocks = EventBlock.objects.filter(is_active=True).order_by('order')
        for i, block in enumerate(blocks):
            if block.order != i:
                block.order = i
                block.save()
        
        # Получаем параметры фильтрации
        category_id = self.request.query_params.get('category_id')
        subcategory_id = self.request.query_params.get('subcategory_id')
        
        queryset = EventBlock.objects.filter(is_active=True)
        
        if category_id:
            queryset = queryset.filter(subcategory__category_id=category_id)
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)
        
        return queryset.prefetch_related(
            Prefetch(
                'events', 
                queryset=Event.objects.filter(is_active=True).prefetch_related(
                    Prefetch('projects', queryset=Project.objects.select_related('owner'))
                )
            ),
            'subcategory'
        )
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Получить мероприятия для конкретного блока."""
        block = self.get_object()
        events = block.events.filter(is_active=True)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def indicators(self, request, pk=None):
        """Получить целевые показатели для конкретного блока мероприятий."""
        block = self.get_object()
        indicators = block.target_indicators.filter(is_active=True)
        serializer = TargetIndicatorSerializer(indicators, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def safe_delete(self, request, pk=None):
        """Безопасное удаление блока с проверкой использования."""
        block = self.get_object()
        
        # Проверяем, есть ли мероприятия в блоке
        events_count = block.events_count
        
        if events_count > 0:
            return Response({
                'error': 'Блок не может быть удален',
                'message': f'В блоке есть {events_count} мероприятий',
                'events_count': events_count
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Если мероприятий нет, помечаем как неактивный
        block.is_active = False
        block.save()
        
        return Response({'message': 'Блок мероприятий успешно удален'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'])
    def update_order(self, request, pk=None):
        """Обновление порядка блока с автоматическим пересчетом порядка других блоков."""
        block = self.get_object()
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
        
        # Получаем все блоки, отсортированные по порядку
        all_blocks = list(EventBlock.objects.filter(is_active=True).order_by('order'))
        
        # Находим текущий индекс блока в отсортированном списке
        current_index = next((i for i, blk in enumerate(all_blocks) if blk.id == block.id), -1)
        
        if current_index == -1:
            return Response({
                'error': 'Блок не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Если порядок не изменился, ничего не делаем
        if current_index == new_order:
            return Response({'message': 'Порядок не изменился'}, status=status.HTTP_200_OK)
        
        # Создаем новый список с обновленными порядками
        updated_blocks = []
        
        # Создаем новый список блоков без текущего
        other_blocks = [blk for blk in all_blocks if blk.id != block.id]
        
        # Вставляем текущий блок на новую позицию
        if new_order == 0:
            # Вставляем в начало
            updated_blocks.append(block)
            updated_blocks.extend(other_blocks)
        elif new_order >= len(other_blocks):
            # Вставляем в конец
            updated_blocks.extend(other_blocks)
            updated_blocks.append(block)
        else:
            # Вставляем в середину
            updated_blocks.extend(other_blocks[:new_order])
            updated_blocks.append(block)
            updated_blocks.extend(other_blocks[new_order:])
        
        # Устанавливаем правильные порядки для всех блоков
        for i, blk in enumerate(updated_blocks):
            blk.order = i
        
        # Сохраняем все изменения
        for blk in updated_blocks:
            blk.save()
        
        return Response({
            'message': 'Порядок блока успешно обновлен',
            'old_order': current_index,
            'new_order': new_order
        }, status=status.HTTP_200_OK)


class EventViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления мероприятиями."""
    queryset = Event.objects.filter(is_active=True)
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        block_id = self.request.query_params.get('block_id')
        queryset = Event.objects.filter(is_active=True)
        
        if block_id:
            queryset = queryset.filter(block_id=block_id)
        
        return queryset
    
    @action(detail=True, methods=['delete'])
    def safe_delete(self, request, pk=None):
        """Безопасное удаление мероприятия."""
        event = self.get_object()
        
        # Помечаем как неактивное
        event.is_active = False
        event.save()
        
        return Response({'message': 'Мероприятие успешно удалено'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'])
    def update_order(self, request, pk=None):
        """Обновление порядка мероприятия в блоке."""
        event = self.get_object()
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
        
        # Получаем все мероприятия в том же блоке, отсортированные по порядку
        all_events = list(Event.objects.filter(block=event.block, is_active=True).order_by('order'))
        
        # Находим текущий индекс мероприятия в отсортированном списке
        current_index = next((i for i, evt in enumerate(all_events) if evt.id == event.id), -1)
        
        if current_index == -1:
            return Response({
                'error': 'Мероприятие не найдено'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Если порядок не изменился, ничего не делаем
        if current_index == new_order:
            return Response({'message': 'Порядок не изменился'}, status=status.HTTP_200_OK)
        
        # Создаем новый список с обновленными порядками
        updated_events = []
        
        # Создаем новый список мероприятий без текущего
        other_events = [evt for evt in all_events if evt.id != event.id]
        
        # Вставляем текущее мероприятие на новую позицию
        if new_order == 0:
            # Вставляем в начало
            updated_events.append(event)
            updated_events.extend(other_events)
        elif new_order >= len(other_events):
            # Вставляем в конец
            updated_events.extend(other_events)
            updated_events.append(event)
        else:
            # Вставляем в середину
            updated_events.extend(other_events[:new_order])
            updated_events.append(event)
            updated_events.extend(other_events[new_order:])
        
        # Устанавливаем правильные порядки для всех мероприятий
        for i, evt in enumerate(updated_events):
            evt.order = i
        
        # Сохраняем все изменения
        for evt in updated_events:
            evt.save()
        
        return Response({
            'message': 'Порядок мероприятия успешно обновлен',
            'old_order': current_index,
            'new_order': new_order
        }, status=status.HTTP_200_OK)


class ProjectEdRoleViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = ProjectEdRoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectEdAdmin]


class ProjectEdPositionViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = ProjectEdPositionSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectEdAdmin]

    @action(detail=False, methods=['get'])
    def user_counts(self, request):
        """Получить количество пользователей по должностям (включая непубличные профили)."""
        from django.contrib.auth import get_user_model
        from django.db.models import Count
        
        User = get_user_model()
        
        counts = User.objects.filter(
            project_ed_profile__position_ref__isnull=False
        ).values(
            'project_ed_profile__position_ref'
        ).annotate(
            user_count=Count('id')
        )
        
        result = {}
        for item in counts:
            pos_id = item['project_ed_profile__position_ref']
            result[pos_id] = item['user_count']
        
        return Response(result)


class ProjectEdFacultyViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Faculty.objects.prefetch_related('departments').all()
    serializer_class = ProjectEdFacultySerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectEdAdmin]
    
    def get_queryset(self):
        """Переопределяем get_queryset для поддержки поиска по всем полям."""
        from django.db.models import Q
        
        queryset = Faculty.objects.prefetch_related('departments').all()
        search_term = self.request.query_params.get('search', '').strip()
        
        if search_term:
            # Поиск по названию факультета, короткому имени факультета, названию кафедры и короткому имени кафедры
            search_query = Q(
                Q(name__icontains=search_term) |
                Q(short_name__icontains=search_term) |
                Q(departments__name__icontains=search_term) |
                Q(departments__short_name__icontains=search_term)
            )
            queryset = queryset.filter(search_query).distinct()
        
        return queryset

    @action(detail=False, methods=['get'])
    def department_counts(self, request):
        """Получить количество кафедр по факультетам."""
        from django.db.models import Count
        
        counts = Department.objects.filter(
            faculty__isnull=False
        ).values(
            'faculty'
        ).annotate(
            department_count=Count('id')
        )
        
        result = {}
        for item in counts:
            faculty_id = item['faculty']
            result[faculty_id] = item['department_count']
        
        return Response(result)

    @action(detail=False, methods=['get'])
    def user_counts(self, request):
        """Получить количество пользователей по факультетам (включая непубличные профили)."""
        from django.contrib.auth import get_user_model
        from django.db.models import Count
        
        User = get_user_model()
        
        counts = User.objects.filter(
            project_ed_profile__faculty_ref__isnull=False
        ).values(
            'project_ed_profile__faculty_ref'
        ).annotate(
            user_count=Count('id')
        )
        
        result = {}
        for item in counts:
            faculty_id = item['project_ed_profile__faculty_ref']
            result[faculty_id] = item['user_count']
        
        return Response(result)


class ProjectEdDepartmentViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Department.objects.select_related('faculty').all()
    serializer_class = ProjectEdDepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectEdAdmin]
    
    def get_queryset(self):
        """Переопределяем get_queryset для поддержки поиска по всем полям."""
        from django.db.models import Q
        
        queryset = Department.objects.select_related('faculty').all()
        search_term = self.request.query_params.get('search', '').strip()
        
        if search_term:
            # Поиск по названию кафедры, короткому имени кафедры, названию факультета и короткому имени факультета
            search_query = Q(
                Q(name__icontains=search_term) |
                Q(short_name__icontains=search_term) |
                Q(faculty__name__icontains=search_term) |
                Q(faculty__short_name__icontains=search_term)
            )
            queryset = queryset.filter(search_query)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def user_counts(self, request):
        """Получить количество пользователей по кафедрам (включая непубличные профили)."""
        from django.contrib.auth import get_user_model
        from django.db.models import Count
        
        User = get_user_model()
        
        # Подсчитываем пользователей по кафедрам, включая всех пользователей
        # (не только с публичными профилями)
        counts = User.objects.filter(
            project_ed_profile__department_ref__isnull=False
        ).values(
            'project_ed_profile__department_ref'
        ).annotate(
            user_count=Count('id')
        )
        
        # Преобразуем в словарь для удобства
        result = {}
        for item in counts:
            dept_id = item['project_ed_profile__department_ref']
            result[dept_id] = item['user_count']
        
        return Response(result)