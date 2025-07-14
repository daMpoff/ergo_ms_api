from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from src.core.utils.mixins import SwaggerSafeMixin

from .models import (
    Project, ProjectMember, Task, TaskComment, TaskAttachment, TimeLog,
    ProjectStatus, ProjectPriority, TaskStatus, TaskPriority
)
from .serializers import (
    ProjectSerializer, ProjectListSerializer, ProjectMemberSerializer,
    TaskSerializer, TaskListSerializer, TaskCalendarSerializer, TaskKanbanSerializer,
    TaskCommentSerializer, TaskAttachmentSerializer, TimeLogSerializer, CRMUserSerializer,
    ProjectStatusSerializer, ProjectPrioritySerializer, TaskStatusSerializer, TaskPrioritySerializer
)

User = get_user_model()


class ProjectStatusViewSet(viewsets.ModelViewSet):
    """ViewSet для управления статусами проектов"""
    queryset = ProjectStatus.objects.filter(is_active=True)
    serializer_class = ProjectStatusSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить только активные статусы"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Получить статус по умолчанию"""
        try:
            default_status = self.get_queryset().get(is_default=True)
            serializer = self.get_serializer(default_status)
            return Response(serializer.data)
        except ProjectStatus.DoesNotExist:
            return Response({'error': 'Статус по умолчанию не найден'}, status=status.HTTP_404_NOT_FOUND)


class ProjectPriorityViewSet(viewsets.ModelViewSet):
    """ViewSet для управления приоритетами проектов"""
    queryset = ProjectPriority.objects.filter(is_active=True)
    serializer_class = ProjectPrioritySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['level', 'name', 'created_at']
    ordering = ['level', 'name']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить только активные приоритеты"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Получить приоритет по умолчанию"""
        try:
            default_priority = self.get_queryset().get(is_default=True)
            serializer = self.get_serializer(default_priority)
            return Response(serializer.data)
        except ProjectPriority.DoesNotExist:
            return Response({'error': 'Приоритет по умолчанию не найден'}, status=status.HTTP_404_NOT_FOUND)


class TaskStatusViewSet(viewsets.ModelViewSet):
    """ViewSet для управления статусами задач"""
    queryset = TaskStatus.objects.filter(is_active=True)
    serializer_class = TaskStatusSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить только активные статусы"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def kanban_columns(self, request):
        """Получить статусы для колонок канбан (все активные статусы)"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Получить статус по умолчанию"""
        try:
            default_status = self.get_queryset().get(is_default=True)
            serializer = self.get_serializer(default_status)
            return Response(serializer.data)
        except TaskStatus.DoesNotExist:
            return Response({'error': 'Статус по умолчанию не найден'}, status=status.HTTP_404_NOT_FOUND)


class TaskPriorityViewSet(viewsets.ModelViewSet):
    """ViewSet для управления приоритетами задач"""
    queryset = TaskPriority.objects.filter(is_active=True)
    serializer_class = TaskPrioritySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['level', 'name', 'created_at']
    ordering = ['level', 'name']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить только активные приоритеты"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Получить приоритет по умолчанию"""
        try:
            default_priority = self.get_queryset().get(is_default=True)
            serializer = self.get_serializer(default_priority)
            return Response(serializer.data)
        except TaskPriority.DoesNotExist:
            return Response({'error': 'Приоритет по умолчанию не найден'}, status=status.HTTP_404_NOT_FOUND)


class ProjectViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления проектами"""
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'owner', 'manager']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Project.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Project.objects.none()
            
        queryset = super().get_queryset()
        
        # По умолчанию показываем только проекты, в которых пользователь участвует
        # Это включает: владельца, менеджера и участников команды
        queryset = queryset.filter(
            Q(owner=user) | 
            Q(manager=user) | 
            Q(team_members=user)
        ).distinct()
        
        # Дополнительный фильтр "Мои проекты" (оставляем для совместимости)
        my_projects = self.request.query_params.get('my_projects', None)
        if my_projects and my_projects.lower() == 'false':
            # Если явно указано false, показываем все доступные проекты
            queryset = super().get_queryset()
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Добавить участника в проект"""
        project = self.get_object()
        serializer = ProjectMemberSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Проверяем, не является ли пользователь уже участником
                user_id = serializer.validated_data['user_id']
                if ProjectMember.objects.filter(project=project, user_id=user_id).exists():
                    return Response({'error': 'Пользователь уже является участником проекта'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                member = serializer.save(project=project)
                
                # Возвращаем полные данные участника
                response_serializer = ProjectMemberSerializer(member)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """Удалить участника из проекта"""
        project = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            membership = ProjectMember.objects.get(project=project, user_id=user_id)
            membership.delete()
            return Response({'message': 'Участник удален из проекта'})
        except ProjectMember.DoesNotExist:
            return Response({'error': 'Участник не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """Получить задачи проекта"""
        project = self.get_object()
        tasks = project.tasks.all()
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Получить статистику проекта"""
        project = self.get_object()
        
        total_tasks = project.tasks.count()
        
        # Завершенные задачи с учетом новой и старой системы статусов
        completed_tasks = project.tasks.filter(
            Q(status_ref__is_final=True, status_ref__is_active=True) | Q(status='done')
        ).count()
        
        # Задачи в работе с учетом новой системы
        in_progress_tasks = project.tasks.filter(
            Q(status_ref__code='in_progress', status_ref__is_active=True) | Q(status='in_progress')
        ).count()
        
        # Просроченные задачи - которые не завершены и срок прошел
        overdue_tasks = project.tasks.filter(
            due_date__lt=timezone.now()
        ).exclude(
            Q(status_ref__is_final=True, status_ref__is_active=True) | Q(status='done')
        ).count()
        
        return Response({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'overdue_tasks': overdue_tasks,
            'progress': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)
        })


class TaskViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления задачами"""
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'project', 'assignee', 'creator']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'kanban_order']
    ordering = ['kanban_order', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'calendar':
            return TaskCalendarSerializer
        elif self.action == 'kanban':
            return TaskKanbanSerializer
        return TaskSerializer
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Task.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Task.objects.none()
            
        queryset = super().get_queryset()
        
        # Параметр "Мои задачи" 
        my_tasks = self.request.query_params.get('my_tasks', None)
        
        if my_tasks and my_tasks.lower() == 'true':
            # Только мои задачи - только задачи, где я исполнитель
            queryset = queryset.filter(assignee=user).distinct()
        else:
            # Показываем все задачи из проектов, в которых пользователь участвует
            # Это включает: владельца проекта, менеджера проекта, участников команды, 
            # исполнителей задач и создателей задач
            queryset = queryset.filter(
                Q(project__owner=user) |
                Q(project__manager=user) |
                Q(project__team_members=user) |
                Q(assignee=user) |
                Q(creator=user)
            ).distinct()
        
        # Фильтр по дате для календаря
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(
                Q(start_date__range=[start_date, end_date]) |
                Q(due_date__range=[start_date, end_date])
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Получить задачи для календаря"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            # По умолчанию текущий месяц
            now = timezone.now()
            start_date = now.replace(day=1).date()
            end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        
        tasks = self.get_queryset().filter(
            Q(start_date__range=[start_date, end_date]) |
            Q(due_date__range=[start_date, end_date])
        )
        
        serializer = TaskCalendarSerializer(tasks, many=True)
        
        # Преобразуем в формат для календаря
        events = []
        for task in serializer.data:
            # Событие начала задачи
            if task['start_date']:
                events.append({
                    'id': f"start_{task['id']}",
                    'title': f"▶ {task['title']}",
                    'start': task['start_date'],
                    'backgroundColor': self.get_task_color(task['priority'], task['status']),
                    'task_id': task['id'],
                    'type': 'start',
                    'task_data': task
                })
            
            # Событие срока выполнения
            if task['due_date']:
                events.append({
                    'id': f"due_{task['id']}",
                    'title': f"⏰ {task['title']}",
                    'start': task['due_date'],
                    'backgroundColor': self.get_due_color(task['priority'], task['status']),
                    'task_id': task['id'],
                    'type': 'due',
                    'task_data': task
                })
        
        return Response({'events': events})
    
    def get_task_color(self, priority, status):
        """Получить цвет задачи для календаря"""
        if status == 'done':
            return '#28a745'  # Зеленый для выполненных
        elif status == 'cancelled':
            return '#6c757d'  # Серый для отмененных
        elif priority == 'urgent':
            return '#dc3545'  # Красный для срочных
        elif priority == 'high':
            return '#fd7e14'  # Оранжевый для высокого приоритета
        elif priority == 'medium':
            return '#007bff'  # Синий для среднего приоритета
        else:
            return '#6f42c1'  # Фиолетовый для низкого приоритета
    
    def get_due_color(self, priority, status):
        """Получить цвет срока выполнения"""
        if status == 'done':
            return '#28a745'
        elif priority == 'urgent':
            return '#dc3545'
        else:
            return '#ffc107'  # Желтый для сроков
    
    @action(detail=False, methods=['get'])
    def kanban(self, request):
        """Получить задачи для канбан доски"""
        project_id = request.query_params.get('project_id')
        priority = request.query_params.get('priority')
        assignee = request.query_params.get('assignee')
        ordering = request.query_params.get('ordering', 'kanban_order')
        
        queryset = self.get_queryset()
        
        # Применяем фильтры
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        if priority:
            queryset = queryset.filter(priority=priority)
            
        if assignee:
            queryset = queryset.filter(assignee_id=assignee)
        
        # Применяем сортировку
        ordering_fields = {
            'kanban_order': ['kanban_order', '-created_at'],
            '-created_at': ['-created_at'],
            'created_at': ['created_at'],
            'due_date': ['due_date', '-created_at'],
            '-due_date': ['-due_date', '-created_at'],
            'priority': ['priority_ref__level', 'priority', '-created_at'],
            '-priority': ['-priority_ref__level', '-priority', '-created_at'],
            'assignee': ['assignee__first_name', 'assignee__last_name', '-created_at'],
            '-assignee': ['-assignee__first_name', '-assignee__last_name', '-created_at']
        }
        
        # Применяем сортировку с fallback
        ordering_list = ordering_fields.get(ordering, ['kanban_order', '-created_at'])
        queryset = queryset.order_by(*ordering_list)
        
        # Получаем все активные статусы задач
        try:
            # Используем все активные статусы
            kanban_statuses = TaskStatus.objects.filter(is_active=True).order_by('order', 'name')
        except Exception:
            # Fallback: используем старые статусы
            kanban_statuses = []
        
        # Группируем по статусам
        kanban_data = {}
        
        if kanban_statuses:
            # Используем динамические статусы
            for status in kanban_statuses:
                tasks = queryset.filter(status=status.code)
                serializer = TaskKanbanSerializer(tasks, many=True)
                kanban_data[status.code] = serializer.data
        else:
            # Fallback к старым жестко заданным статусам
            fallback_statuses = ['todo', 'in_progress', 'review', 'done']
            for status_key in fallback_statuses:
                tasks = queryset.filter(status=status_key)
                serializer = TaskKanbanSerializer(tasks, many=True)
                kanban_data[status_key] = serializer.data
        
        return Response(kanban_data)
    
    @action(detail=True, methods=['post'])
    def update_kanban_order(self, request, pk=None):
        """Обновить порядок задач в канбан"""
        task = self.get_object()
        new_order = request.data.get('order')
        new_status = request.data.get('status')
        
        if new_order is not None:
            task.kanban_order = new_order
        
        if new_status:
            # Проверяем существование статуса в новой системе
            try:
                status_obj = TaskStatus.objects.get(code=new_status, is_active=True)
                task.status = new_status
                task.status_ref = status_obj
                
                # Если задача помечена как выполненная
                if status_obj.is_final and not task.completed_at:
                    task.completed_at = timezone.now()
                elif not status_obj.is_final:
                    task.completed_at = None
                
            except TaskStatus.DoesNotExist:
                # Fallback: проверяем по старым choices
                if new_status in dict(Task.TASK_STATUS_CHOICES):
                    task.status = new_status
                    
                    # Для обратной совместимости
                    if new_status == 'done' and not task.completed_at:
                        task.completed_at = timezone.now()
                    elif new_status != 'done':
                        task.completed_at = None
                else:
                    return Response({'error': f'Неверный статус: {new_status}'}, status=status.HTTP_400_BAD_REQUEST)
        
        task.save()
        return Response({'message': 'Порядок задач обновлен'})
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Изменить статус задачи"""
        task = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Task.TASK_STATUS_CHOICES):
            return Response({'error': 'Неверный статус'}, status=status.HTTP_400_BAD_REQUEST)
        
        task.status = new_status
        
        if new_status == 'done':
            task.completed_at = timezone.now()
        elif new_status == 'in_progress' and not task.start_date:
            task.start_date = timezone.now()
        
        task.save()
        return Response({'message': 'Статус задачи изменен'})
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Добавить комментарий к задаче"""
        task = self.get_object()
        serializer = TaskCommentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save(task=task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_time_log(self, request, pk=None):
        """Добавить учет времени"""
        task = self.get_object()
        serializer = TimeLogSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save(task=task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def create_from_calendar(self, request):
        """Создать задачу из календаря"""
        data = request.data.copy()
        
        # Если не указан проект, пытаемся найти активный проект пользователя
        if not data.get('project_id'):
            active_project = Project.objects.filter(
                Q(owner=request.user) | Q(manager=request.user),
                status='active'
            ).first()
            
            if active_project:
                data['project_id'] = active_project.id
            else:
                return Response(
                    {'error': 'Необходимо указать проект'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = TaskSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskCommentViewSet(viewsets.ModelViewSet):
    """ViewSet для комментариев к задачам"""
    queryset = TaskComment.objects.all()
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return queryset


class TimeLogViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для учета времени"""
    queryset = TimeLog.objects.all()
    serializer_class = TimeLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'user', 'date']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return TimeLog.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return TimeLog.objects.none()
            
        queryset = super().get_queryset()
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_time_logs(self, request):
        """Получить мои записи времени"""
        queryset = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для получения пользователей (только чтение)"""
    queryset = User.objects.filter(is_active=True)
    serializer_class = CRMUserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name']
    ordering = ['first_name', 'last_name', 'username']