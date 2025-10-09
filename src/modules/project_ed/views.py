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
from django.db import transaction
from django.utils import timezone
from src.modules.project_ed.projects.models import (
    ProjectVersion,
    ProjectAuditLog,
    ProjectBudgetItem,
    ProjectBudgetTotal,
    ProjectStage,
    ProjectPlannedResult,
    ProjectTask,
)
from src.modules.project_ed.projects.models import ProjectTargetIndicator
from src.modules.project_ed.projects.serializers import ProjectAuditLogSerializer


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
        'executors__user__project_ed_profile__position_ref',
        'budget_items__stage',
        'budget_totals',
        'tasks',
        'planned_results',
        'target_indicators_rel',
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

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Переопределяем destroy для записи аудита при удалении проекта."""
        instance = self.get_object()
        
        # Записываем аудит удаления проекта
        try:
            from .models import ProjectAuditLog
            import json
            
            # Собираем основную информацию о проекте для аудита
            project_data = {
                'id': instance.id,
                'short_name': instance.short_name,
                'name': instance.name,
                'status': instance.status,
                'owner_id': instance.owner_id,
                'manager_id': instance.manager_id,
                'curator_id': instance.curator_id,
                'customer_id': instance.customer_id,
                'start_date': instance.start_date.isoformat() if instance.start_date else None,
                'end_date': instance.end_date.isoformat() if instance.end_date else None,
                'budget_total': float(instance.budget_total) if instance.budget_total else 0,
                'created_at': instance.created_at.isoformat() if instance.created_at else None,
                'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
            }
            
            # Записываем аудит удаления
            ProjectAuditLog.log_action(
                project=instance,
                action=ProjectAuditLog.ActionType.DELETE,
                user=getattr(request, 'user', None),
                model_type=ProjectAuditLog.ModelType.PROJECT,
                object_id=instance.id,
                field_name='project',
                old_value=json.dumps(project_data, ensure_ascii=False),
                new_value='',
                metadata={
                    'source': 'api', 
                    'view': 'ProjectViewSet.destroy',
                    'deleted_related_data': {
                        'tasks_count': instance.tasks.count(),
                        'executors_count': instance.executors.count(),
                        'planned_results_count': instance.planned_results.count(),
                        'target_indicators_count': instance.target_indicators_rel.count(),
                        'stages_count': instance.stages.count(),
                        'budget_items_count': instance.budget_items.count(),
                        'user_roles_count': instance.user_roles.count(),
                        'versions_count': instance.versions.count(),
                    }
                },
                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                description='Полное удаление проекта и всех связанных данных',
            )
        except Exception as e:
            # Ошибки аудита не должны блокировать удаление
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка записи аудита при удалении проекта {instance.id}: {e}")
        
        # Выполняем стандартное удаление
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Захватываем старые значения редактируемых полей
        editable_fields = set(getattr(request, 'data', {}) .keys())
        old_values = {}
        for field in editable_fields:
            if hasattr(instance, field):
                try:
                    old_values[field] = getattr(instance, field)
                except Exception:
                    pass

        # Извлекаем целевые показатели из payload до сериализации (чтобы не упасть на неописанном поле)
        payload_data = dict(request.data) if hasattr(request, 'data') else {}
        target_indicators_payload = payload_data.pop('target_indicators', None)
        planned_results_payload = payload_data.pop('planned_results', None)
        tasks_payload = payload_data.pop('tasks', None)
        executors_payload = payload_data.pop('executors', None)

        serializer = self.get_serializer(instance, data=payload_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # --- Обработка бюджета (итоги и позиции) ---
        try:
            from decimal import Decimal, ROUND_HALF_UP
            import json

            def to_dec(value):
                try:
                    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                except Exception:
                    return Decimal('0.00')

            payload_totals = request.data.get('budget_totals')
            payload_items = request.data.get('budget_items')

            # Снимки старых значений для аудита
            old_totals_obj = instance.budget_totals.first()
            old_totals_data = None
            if old_totals_obj:
                old_totals_data = {
                    'total_with_insurance': float(old_totals_obj.total_with_insurance),
                    'salary_off_budget': float(old_totals_obj.salary_off_budget),
                    'salary_budget': float(old_totals_obj.salary_budget),
                    'other_off_budget': float(old_totals_obj.other_off_budget),
                    'other_budget': float(old_totals_obj.other_budget),
                }

            old_items_data = [
                {
                    'id': itm.id,
                    'stage_id': itm.stage_id,
                    'cost_article': itm.cost_article,
                    'funding_source': itm.funding_source,
                    'amount': float(itm.amount),
                }
                for itm in instance.budget_items.select_related('stage').all()
            ]

            # Обновление итогов бюджета (upsert одиночной записи)
            if isinstance(payload_totals, dict):
                totals_obj = instance.budget_totals.first() or ProjectBudgetTotal(project=instance)
                totals_obj.total_with_insurance = to_dec(payload_totals.get('total_with_insurance') or 0)
                totals_obj.salary_off_budget = to_dec(payload_totals.get('salary_off_budget') or 0)
                totals_obj.salary_budget = to_dec(payload_totals.get('salary_budget') or 0)
                totals_obj.other_off_budget = to_dec(payload_totals.get('other_off_budget') or 0)
                totals_obj.other_budget = to_dec(payload_totals.get('other_budget') or 0)
                totals_obj.save()
                # Не записываем аудит изменения итогов: общий бюджет пересчитывается системой автоматически

            # Полная замена списка позиций бюджета
            if isinstance(payload_items, list):
                # Удаляем старые позиции проекта
                instance.budget_items.all().delete()
                bulk = []
                for it in payload_items:
                    if not isinstance(it, dict):
                        continue
                    bulk.append(ProjectBudgetItem(
                        project=instance,
                        stage_id=it.get('stage_id') or None,
                        cost_article=str(it.get('cost_article') or ''),
                        funding_source=str(it.get('funding_source') or ''),
                        amount=to_dec(it.get('amount') or 0),
                    ))
                if bulk:
                    ProjectBudgetItem.objects.bulk_create(bulk)

                # Аудит изменения позиций бюджета (агрегированная запись)
                try:
                    new_items_qs = instance.budget_items.all()
                    new_items_data = [
                        {
                            'id': itm.id,
                            'stage_id': itm.stage_id,
                            'cost_article': itm.cost_article,
                            'funding_source': itm.funding_source,
                            'amount': float(itm.amount),
                        }
                        for itm in new_items_qs
                    ]
                    ProjectAuditLog.log_action(
                        project=instance,
                        action=ProjectAuditLog.ActionType.BUDGET_CHANGE,
                        user=getattr(request, 'user', None),
                        model_type=ProjectAuditLog.ModelType.PROJECT_BUDGET_ITEM,
                        object_id=None,
                        field_name='budget_items',
                        old_value=json.dumps(old_items_data, ensure_ascii=False),
                        new_value=json.dumps(new_items_data, ensure_ascii=False),
                        metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                        ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                        user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                        description='Изменение позиций бюджета',
                    )
                except Exception:
                    pass
        except Exception:
            # Ошибки сохранения бюджета не должны валить обновление прочих полей
            pass

        # --- Обработка планируемых результатов ---
        try:
            if isinstance(planned_results_payload, list):
                import json as _json
                # Снимок старых результатов
                old_qs = list(instance.planned_results.all())
                old_items = [
                    { 'id': pr.id, 'description': pr.description, 'order': pr.order }
                    for pr in old_qs
                ]

                # Нормализуем новые результаты
                new_items = []
                for idx, item in enumerate(planned_results_payload):
                    if isinstance(item, dict):
                        desc = (item.get('description') or '').strip()
                        order = item.get('order', idx)
                    else:
                        desc = (str(item) if item is not None else '').strip()
                        order = idx
                    if not desc:
                        continue
                    new_items.append({ 'description': desc, 'order': order })

                # Подсчёт множеств для add/delete
                from collections import Counter, defaultdict
                old_counter = Counter((it['description'], it['order']) for it in old_items)
                new_counter = Counter((it['description'], it['order']) for it in new_items)

                # Изменение порядка: попытаемся определить по совпадающему описанию
                old_by_desc = defaultdict(list)
                for it in old_items:
                    old_by_desc[it['description']].append(it['order'])
                new_by_desc = defaultdict(list)
                for it in new_items:
                    new_by_desc[it['description']].append(it['order'])

                # Пер-айтемное логирование
                # 1) Обновления (смена порядка при том же описании)
                for desc, old_orders in old_by_desc.items():
                    if desc in new_by_desc:
                        new_orders = new_by_desc[desc][:]
                        # Зафиксируем изменения порядка по паре списков
                        # Берём минимально возможное число пар для сравнения по длине
                        # Остатки уйдут в добавления/удаления
                        common = min(len(old_orders), len(new_orders))
                        # Сравниваем по позициям (порядок внутри одинаковых описаний не критичен, но даёт эвристику)
                        for i in range(common):
                            if old_orders[i] != new_orders[i]:
                                try:
                                    ProjectAuditLog.log_action(
                                        project=instance,
                                        action=ProjectAuditLog.ActionType.UPDATE,
                                        user=getattr(request, 'user', None),
                                        model_type=ProjectAuditLog.ModelType.PROJECT_PLANNED_RESULT,
                                        object_id=None,
                                        field_name='planned_result.order',
                                        old_value=str(old_orders[i]),
                                        new_value=str(new_orders[i]),
                                        metadata={'source': 'api', 'view': 'ProjectViewSet.update', 'description': desc},
                                        ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                        user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                        description=f"Изменён порядок планируемого результата: '{desc}'",
                                    )
                                except Exception:
                                    pass

                # 2) Удаления
                for key, cnt in (old_counter - new_counter).items():
                    desc, order = key
                    for _ in range(cnt):
                        try:
                            ProjectAuditLog.log_action(
                                project=instance,
                                action=ProjectAuditLog.ActionType.DELETE,
                                user=getattr(request, 'user', None),
                                model_type=ProjectAuditLog.ModelType.PROJECT_PLANNED_RESULT,
                                object_id=None,
                                field_name='planned_result',
                                old_value=_json.dumps({'description': desc, 'order': order}, ensure_ascii=False),
                                new_value='',
                                metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                description=f"Удалён планируемый результат: '{desc}'",
                            )
                        except Exception:
                            pass

                # 3) Добавления
                for key, cnt in (new_counter - old_counter).items():
                    desc, order = key
                    for _ in range(cnt):
                        try:
                            ProjectAuditLog.log_action(
                                project=instance,
                                action=ProjectAuditLog.ActionType.CREATE,
                                user=getattr(request, 'user', None),
                                model_type=ProjectAuditLog.ModelType.PROJECT_PLANNED_RESULT,
                                object_id=None,
                                field_name='planned_result',
                                old_value='',
                                new_value=_json.dumps({'description': desc, 'order': order}, ensure_ascii=False),
                                metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                description=f"Добавлен планируемый результат: '{desc}'",
                            )
                        except Exception:
                            pass

                # Полная замена записей в БД под текущий payload
                instance.planned_results.all().delete()
                bulk = [
                    ProjectPlannedResult(project=instance, description=it['description'], order=it['order'])
                    for it in new_items
                ]
                if bulk:
                    ProjectPlannedResult.objects.bulk_create(bulk)

                # Агрегированная запись об изменениях всего списка
                try:
                    ProjectAuditLog.log_action(
                        project=instance,
                        action=ProjectAuditLog.ActionType.UPDATE,
                        user=getattr(request, 'user', None),
                        model_type=ProjectAuditLog.ModelType.PROJECT_PLANNED_RESULT,
                        object_id=None,
                        field_name='planned_results',
                        old_value=_json.dumps(old_items, ensure_ascii=False),
                        new_value=_json.dumps(new_items, ensure_ascii=False),
                        metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                        ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                        user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                        description='Обновление списка планируемых результатов',
                    )
                except Exception:
                    pass
        except Exception:
            # Ошибки обработки планируемых результатов не должны валить обновление прочих полей
            pass

        # --- Обработка задач проекта ---
        try:
            if isinstance(tasks_payload, list):
                import json as _json
                # Снимок старых задач
                old_qs = list(instance.tasks.all())
                old_items = [
                    { 'id': t.id, 'description': t.description, 'order': t.order }
                    for t in old_qs
                ]

                # Нормализуем новые задачи
                new_items = []
                for idx, item in enumerate(tasks_payload):
                    if isinstance(item, dict):
                        desc = (item.get('description') or item.get('title') or '').strip()
                        order = item.get('order', idx)
                    else:
                        desc = (str(item) if item is not None else '').strip()
                        order = idx
                    if not desc:
                        continue
                    new_items.append({ 'description': desc, 'order': order })

                from collections import Counter, defaultdict
                old_counter = Counter((it['description'], it['order']) for it in old_items)
                new_counter = Counter((it['description'], it['order']) for it in new_items)

                # Изменение порядка по совпадающему описанию
                old_by_desc = defaultdict(list)
                for it in old_items:
                    old_by_desc[it['description']].append(it['order'])
                new_by_desc = defaultdict(list)
                for it in new_items:
                    new_by_desc[it['description']].append(it['order'])

                for desc, old_orders in old_by_desc.items():
                    if desc in new_by_desc:
                        new_orders = new_by_desc[desc][:]
                        common = min(len(old_orders), len(new_orders))
                        for i in range(common):
                            if old_orders[i] != new_orders[i]:
                                try:
                                    ProjectAuditLog.log_action(
                                        project=instance,
                                        action=ProjectAuditLog.ActionType.UPDATE,
                                        user=getattr(request, 'user', None),
                                        model_type=ProjectAuditLog.ModelType.PROJECT_TASK,
                                        object_id=None,
                                        field_name='task.order',
                                        old_value=str(old_orders[i]),
                                        new_value=str(new_orders[i]),
                                        metadata={'source': 'api', 'view': 'ProjectViewSet.update', 'description': desc},
                                        ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                        user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                        description=f"Изменён порядок задачи: '{desc}'",
                                    )
                                except Exception:
                                    pass

                # Удаления
                for key, cnt in (old_counter - new_counter).items():
                    desc, order = key
                    for _ in range(cnt):
                        try:
                            ProjectAuditLog.log_action(
                                project=instance,
                                action=ProjectAuditLog.ActionType.DELETE,
                                user=getattr(request, 'user', None),
                                model_type=ProjectAuditLog.ModelType.PROJECT_TASK,
                                object_id=None,
                                field_name='task',
                                old_value=_json.dumps({'description': desc, 'order': order}, ensure_ascii=False),
                                new_value='',
                                metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                description=f"Удалена задача: '{desc}'",
                            )
                        except Exception:
                            pass

                # Добавления
                for key, cnt in (new_counter - old_counter).items():
                    desc, order = key
                    for _ in range(cnt):
                        try:
                            ProjectAuditLog.log_action(
                                project=instance,
                                action=ProjectAuditLog.ActionType.CREATE,
                                user=getattr(request, 'user', None),
                                model_type=ProjectAuditLog.ModelType.PROJECT_TASK,
                                object_id=None,
                                field_name='task',
                                old_value='',
                                new_value=_json.dumps({'description': desc, 'order': order}, ensure_ascii=False),
                                metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                description=f"Добавлена задача: '{desc}'",
                            )
                        except Exception:
                            pass

                # Полная замена в БД
                instance.tasks.all().delete()
                bulk = [
                    ProjectTask(project=instance, description=it['description'], order=it['order'])
                    for it in new_items
                ]
                if bulk:
                    ProjectTask.objects.bulk_create(bulk)

                # Агрегированная запись
                try:
                    ProjectAuditLog.log_action(
                        project=instance,
                        action=ProjectAuditLog.ActionType.UPDATE,
                        user=getattr(request, 'user', None),
                        model_type=ProjectAuditLog.ModelType.PROJECT_TASK,
                        object_id=None,
                        field_name='tasks',
                        old_value=_json.dumps(old_items, ensure_ascii=False),
                        new_value=_json.dumps(new_items, ensure_ascii=False),
                        metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                        ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                        user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                        description='Обновление списка задач проекта',
                    )
                except Exception:
                    pass
        except Exception:
            # Ошибки обработки задач не должны валить обновление прочих полей
            pass

        # --- Обработка исполнителей проекта ---
        try:
            if isinstance(executors_payload, list):
                import json as _json
                # Текущее состояние
                old_qs = list(instance.executors.all())
                old_ids = [link.user_id for link in old_qs]
                # Нормализуем новые id
                new_ids = []
                for v in executors_payload:
                    try:
                        n = int(v)
                    except Exception:
                        continue
                    if n not in new_ids:
                        new_ids.append(n)

                old_set = set(old_ids)
                new_set = set(new_ids)

                removed = sorted(list(old_set - new_set))
                added = sorted(list(new_set - old_set))

                # Логирование
                for uid in removed:
                    try:
                        ProjectAuditLog.log_action(
                            project=instance,
                            action=ProjectAuditLog.ActionType.ROLE_REMOVE,
                            user=getattr(request, 'user', None),
                            model_type=ProjectAuditLog.ModelType.PROJECT_EXECUTOR,
                            object_id=uid,
                            field_name='executor',
                            old_value=str(uid),
                            new_value='',
                            metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                            ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                            user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                            description=f'Удалён исполнитель {uid}',
                        )
                    except Exception:
                        pass

                for uid in added:
                    try:
                        ProjectAuditLog.log_action(
                            project=instance,
                            action=ProjectAuditLog.ActionType.ROLE_ASSIGN,
                            user=getattr(request, 'user', None),
                            model_type=ProjectAuditLog.ModelType.PROJECT_EXECUTOR,
                            object_id=uid,
                            field_name='executor',
                            old_value='',
                            new_value=str(uid),
                            metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                            ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                            user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                            description=f'Добавлен исполнитель {uid}',
                        )
                    except Exception:
                        pass

                # Синхронизация в БД
                from src.modules.project_ed.projects.models import ProjectExecutor
                # Удаляем лишние
                instance.executors.exclude(user_id__in=new_ids).delete()
                # Добавляем недостающие
                to_create = [uid for uid in new_ids if uid not in old_set]
                if to_create:
                    ProjectExecutor.objects.bulk_create([
                        ProjectExecutor(project=instance, user_id=uid)
                        for uid in to_create
                    ], ignore_conflicts=True)
        except Exception:
            # Ошибки обработки исполнителей не должны валить обновление прочих полей
            pass

        # --- Обработка этапов (создание/обновление/удаление) ---
        try:
            import json
            payload_stages = request.data.get('stages')
            if isinstance(payload_stages, list):
                # Текущее состояние
                existing_qs = list(instance.stages.all())
                by_id = {s.id: s for s in existing_qs}

                # Идентификаторы из payload
                seen_ids = set()

                def user_display_name(u):
                    try:
                        first = (getattr(u, 'first_name', '') or '').strip()
                        last = (getattr(u, 'last_name', '') or '').strip()
                        full = f"{first} {last}".strip()
                        return full or getattr(u, 'username', '') or 'Пользователь'
                    except Exception:
                        return 'Пользователь'

                actor = user_display_name(getattr(request, 'user', None))

                # Обновление/создание
                for idx, item in enumerate(payload_stages):
                    if not isinstance(item, dict):
                        continue
                    stage_id = item.get('id')
                    name = item.get('name') or ''
                    start_date = item.get('start_date') or item.get('start') or instance.start_date
                    end_date = item.get('end_date') or item.get('end') or instance.end_date
                    planned_results = item.get('planned_results') or item.get('result') or ''
                    order = item.get('order', idx)

                    if stage_id and stage_id in by_id:
                        s = by_id[stage_id]
                        changed = (
                            (s.name or '') != (name or '') or
                            str(s.start_date) != str(start_date) or
                            str(s.end_date) != str(end_date) or
                            (s.planned_results or '') != (planned_results or '') or
                            s.order != order
                        )
                        if changed:
                            old_snapshot = {
                                'id': s.id,
                                'name': s.name,
                                'start_date': str(s.start_date),
                                'end_date': str(s.end_date),
                                'planned_results': s.planned_results,
                                'order': s.order,
                            }
                            s.name = name or ''
                            s.start_date = start_date
                            s.end_date = end_date
                            s.planned_results = planned_results or ''
                            s.order = order
                            s.save()
                            try:
                                ProjectAuditLog.log_action(
                                    project=instance,
                                    action=ProjectAuditLog.ActionType.STAGE_UPDATE,
                                    user=getattr(request, 'user', None),
                                    model_type=ProjectAuditLog.ModelType.PROJECT_STAGE,
                                    object_id=getattr(s, 'id', None),
                                    field_name='project_stage',
                                    old_value=json.dumps(old_snapshot, ensure_ascii=False),
                                    new_value=json.dumps({
                                        'id': s.id,
                                        'name': s.name,
                                        'start_date': str(s.start_date),
                                        'end_date': str(s.end_date),
                                        'planned_results': s.planned_results,
                                        'order': s.order,
                                    }, ensure_ascii=False),
                                    metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                    ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                    user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                    description=f"{actor} обновил этап {name}",
                                )
                            except Exception:
                                pass
                        seen_ids.add(stage_id)
                    else:
                        # Создание
                        new_stage = ProjectStage.objects.create(
                            project=instance,
                            name=name or '',
                            start_date=start_date,
                            end_date=end_date,
                            planned_results=planned_results or '',
                            order=order,
                        )
                        try:
                            ProjectAuditLog.log_action(
                                project=instance,
                                action=ProjectAuditLog.ActionType.STAGE_ADD,
                                user=getattr(request, 'user', None),
                                model_type=ProjectAuditLog.ModelType.PROJECT_STAGE,
                                object_id=getattr(new_stage, 'id', None),
                                field_name='project_stage',
                                old_value='',
                                new_value=json.dumps({
                                    'id': new_stage.id,
                                    'name': new_stage.name,
                                    'start_date': str(new_stage.start_date),
                                    'end_date': str(new_stage.end_date),
                                    'planned_results': new_stage.planned_results,
                                    'order': new_stage.order,
                                }, ensure_ascii=False),
                                metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                description=f"{actor} создал новый этап {name}",
                            )
                        except Exception:
                            pass
                        seen_ids.add(new_stage.id)

                # Удаление отсутствующих
                for s in existing_qs:
                    if s.id not in seen_ids:
                        name = s.name
                        snapshot = {
                            'id': s.id,
                            'name': s.name,
                            'start_date': str(s.start_date),
                            'end_date': str(s.end_date),
                            'planned_results': s.planned_results,
                            'order': s.order,
                        }
                        s.delete()
                        try:
                            ProjectAuditLog.log_action(
                                project=instance,
                                action=ProjectAuditLog.ActionType.STAGE_DELETE,
                                user=getattr(request, 'user', None),
                                model_type=ProjectAuditLog.ModelType.PROJECT_STAGE,
                                object_id=None,
                                field_name='project_stage',
                                old_value=json.dumps(snapshot, ensure_ascii=False),
                                new_value='',
                                metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                                ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                                user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                                description=f"{actor} удалил этап {name}",
                            )
                        except Exception:
                            pass
        except Exception:
            # Ошибки обработки этапов не должны валить обновление прочих полей
            pass

        # --- Обработка целевых показателей проекта ---
        try:
            import json as _json
            # Снимок старых показателей
            old_ti_qs = list(instance.target_indicators_rel.all())
            old_ti_snapshot = [
                {
                    'id': ti.id,
                    'source_indicator_id': getattr(ti, 'source_indicator_id', None),
                    'name': ti.name,
                    'unit': ti.unit,
                    'baseline': float(ti.baseline) if ti.baseline is not None else None,
                    'planned': float(ti.planned) if ti.planned is not None else None,
                }
                for ti in old_ti_qs
            ]

            if isinstance(target_indicators_payload, list):
                # Полная замена списка показателей
                instance.target_indicators_rel.all().delete()

                new_objs = []
                for item in target_indicators_payload:
                    if not isinstance(item, dict):
                        continue
                    source_indicator_id = item.get('source_indicator_id') or item.get('id')
                    name = item.get('name') or ''
                    unit = item.get('unit') or ''
                    baseline = item.get('baseline')
                    planned = item.get('planned')
                    new_objs.append(ProjectTargetIndicator(
                        project=instance,
                        source_indicator_id=source_indicator_id if source_indicator_id else None,
                        name=name,
                        unit=unit,
                        baseline=baseline,
                        planned=planned,
                    ))
                if new_objs:
                    ProjectTargetIndicator.objects.bulk_create(new_objs)

                # Аудит агрегированного изменения показателей
                try:
                    new_qs = list(instance.target_indicators_rel.all())
                    new_snapshot = [
                        {
                            'id': ti.id,
                            'source_indicator_id': getattr(ti, 'source_indicator_id', None),
                            'name': ti.name,
                            'unit': ti.unit,
                            'baseline': float(ti.baseline) if ti.baseline is not None else None,
                            'planned': float(ti.planned) if ti.planned is not None else None,
                        }
                        for ti in new_qs
                    ]
                    ProjectAuditLog.log_action(
                        project=instance,
                        action=ProjectAuditLog.ActionType.UPDATE,
                        user=getattr(request, 'user', None),
                        model_type=ProjectAuditLog.ModelType.PROJECT_TARGET_INDICATOR,
                        object_id=None,
                        field_name='target_indicators',
                        old_value=_json.dumps(old_ti_snapshot, ensure_ascii=False),
                        new_value=_json.dumps(new_snapshot, ensure_ascii=False),
                        metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                        ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                        user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                        description='Обновление целевых показателей проекта',
                    )
                except Exception:
                    pass
        except Exception:
            # Ошибки показателей не должны валить обновление прочих полей
            pass

        # Фиксируем аудит по измененным полям
        for field, old_val in old_values.items():
            try:
                new_val = getattr(instance, field)
            except Exception:
                continue
            # Сравниваем как строки для универсальности
            old_str = '' if old_val is None else str(old_val)
            new_str = '' if new_val is None else str(new_val)
            if old_str != new_str:
                ProjectAuditLog.log_action(
                    project=instance,
                    action=ProjectAuditLog.ActionType.UPDATE,
                    user=getattr(request, 'user', None),
                    model_type=ProjectAuditLog.ModelType.PROJECT,
                    object_id=getattr(instance, 'id', None),
                    field_name=field,
                    old_value=old_str,
                    new_value=new_str,
                    metadata={'source': 'api', 'view': 'ProjectViewSet.update'},
                    ip_address=request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None,
                    user_agent=request.META.get('HTTP_USER_AGENT') if hasattr(request, 'META') else '',
                    description=f'Изменение поля {field}',
                )

        # Создаем новую версию проекта (снимок текущего состояния)
        try:
            snapshot = ProjectDetailSerializer(instance, context={'request': request}).data
            last_version = ProjectVersion.objects.filter(project=instance).order_by('-version_number').first()
            next_number = (last_version.version_number + 1) if last_version else 1
            ProjectVersion.objects.create(
                project=instance,
                version_number=next_number,
                title=f'Обновление {timezone.now().strftime("%Y-%m-%d %H:%M")}',
                payload=snapshot,
                created_by=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            )
        except Exception:
            # Снимок не должен валить обновление проекта
            pass

        # Создаем уведомление при изменении статуса проекта на pending
        try:
            if 'status' in request.data and request.data['status'] == 'pending':
                from src.modules.project_ed.notifications.methods import create_project_submission_notification
                create_project_submission_notification(instance, request.user)
        except Exception:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка создания уведомления для проекта {instance.id}", exc_info=True)

        # Возвращаем актуальные детальные данные
        read = ProjectDetailSerializer(instance, context={'request': request})
        return Response(read.data)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def audit_logs(self, request, pk=None):
        """Возвращает журнал аудита для проекта."""
        project = self.get_object()
        logs = project.audit_logs.select_related('user__avatar').all()

        # Пагинация при необходимости
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = ProjectAuditLogSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProjectAuditLogSerializer(logs, many=True, context={'request': request})
        return Response(serializer.data)


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