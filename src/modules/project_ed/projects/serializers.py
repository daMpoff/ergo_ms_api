from typing import Any, Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model

from django.db import transaction
from django.utils import timezone
import json
from rest_framework import serializers

from src.modules.project_ed.models import Event, EventBlock, Project
from .models import (
    ProjectTask,
    ProjectExecutor,
    ProjectPlannedResult,
    ProjectTargetIndicator,
    ProjectStage,
    ProjectBudgetItem,
    ProjectBudgetTotal,
    ProjectVersion,
    ProjectRole,
    ProjectUserRole,
)


class ProjectCreateSerializer(serializers.Serializer):
    # Плоские поля проекта
    short_name = serializers.CharField()
    name = serializers.CharField()
    name_clarification = serializers.CharField(required=False, allow_blank=True, default='')
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    curator_id = serializers.IntegerField(required=False, allow_null=True)

    # Совместимость с фронтом: строки-имена. Можем проигнорировать как FK, но положить в payload версии
    customer_name = serializers.CharField(required=False, allow_blank=True, default='')
    manager_name = serializers.CharField(required=False, allow_blank=True, default='')

    # Денорм. бюджет (для быстрого списка). Опционально. Принимаем float и округляем сами
    budget_total = serializers.FloatField(required=False)

    # Сырые блоки формы
    event = serializers.JSONField(required=False)
    basic_provisions = serializers.JSONField(required=False)
    target_indicators = serializers.ListField(child=serializers.DictField(), required=False)
    calendar_plan = serializers.DictField(required=False)
    budget = serializers.DictField(required=False)
    additional_info = serializers.DictField(required=False)

    def _extract_event_links(self, event_payload: Any) -> Dict[str, Optional[int]]:
        block_id = None
        event_id = None
        if isinstance(event_payload, dict):
            event_id = event_payload.get('id') or event_payload.get('event_id')
            block_id = (
                event_payload.get('block_id')
                or event_payload.get('blockId')
                or event_payload.get('event_block_id')
                or (event_payload.get('block') or {}).get('id')
            )
        return {'event_block_id': block_id, 'event_id': event_id}

    def _snapshot_payload(self, validated: Dict[str, Any]) -> Dict[str, Any]:
        # Готовим снимок для версии
        return {
            'short_name': validated.get('short_name'),
            'name': validated.get('name'),
            'name_clarification': validated.get('name_clarification', ''),
            'start_date': str(validated.get('start_date')),
            'end_date': str(validated.get('end_date')),
            'curator_id': validated.get('curator_id'),
            'customer_name': validated.get('customer_name', ''),
            'manager_name': validated.get('manager_name', ''),
            'budget_total': str(validated.get('budget_total') or '0'),
            'event': validated.get('event'),
            'basic_provisions': validated.get('basic_provisions', {}),
            'target_indicators': validated.get('target_indicators', []),
            'calendar_plan': validated.get('calendar_plan', {}),
            'budget': validated.get('budget', {}),
            'additional_info': validated.get('additional_info', {}),
        }

    def validate(self, attrs):
        # Проверки дат
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError('Дата начала не может быть позже даты окончания')
        
        # Мягкая нормализация вложенных структур на случай, если пришли строками
        def ensure_dict(value):
            if isinstance(value, dict) or value is None:
                return value or {}
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
            return {}

        def ensure_list_of_dicts(value):
            if value is None:
                return []
            if isinstance(value, list):
                return [v for v in value if isinstance(v, dict)]
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [v for v in parsed if isinstance(v, dict)]
                except Exception:
                    return []
            return []

        attrs['calendar_plan'] = ensure_dict(attrs.get('calendar_plan'))
        attrs['budget'] = ensure_dict(attrs.get('budget'))
        attrs['additional_info'] = ensure_dict(attrs.get('additional_info'))
        attrs['basic_provisions'] = ensure_dict(attrs.get('basic_provisions'))
        attrs['event'] = ensure_dict(attrs.get('event'))
        attrs['target_indicators'] = ensure_list_of_dicts(attrs.get('target_indicators'))
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Project:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        User = get_user_model()

        # Извлекаем связи мероприятия
        event_links = self._extract_event_links(validated_data.get('event'))
        block_obj = None
        event_obj = None
        if event_links['event_block_id']:
            block_obj = EventBlock.objects.filter(id=event_links['event_block_id']).first()
        if event_links['event_id']:
            event_obj = Event.objects.filter(id=event_links['event_id']).first()

        # Создаём проект
        # Округление бюджетов до двух знаков
        def to_dec_2(value: Any) -> Decimal:
            try:
                return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                return Decimal('0.00')

        # Вычисляем роли
        basic_provisions = validated_data.get('basic_provisions') or {}

        curator_id = (
            validated_data.get('curator_id')
            or basic_provisions.get('curator')
        )

        # Менеджер: по умолчанию текущий пользователь, иначе попытаемся найти по имени
        manager_obj = user if user and getattr(user, 'is_authenticated', False) else None
        if manager_obj is None:
            manager_name = basic_provisions.get('manager') or validated_data.get('manager_name')
            if isinstance(manager_name, str) and manager_name.strip():
                # Пробуем найти по username или по совпадению "Имя Фамилия"
                candidate = (
                    User.objects.filter(username=manager_name).first()
                    or User.objects.filter(first_name__icontains=manager_name.split(' ')[0]).first()
                )
                manager_obj = candidate

        # Заказчик: принимаем id (если придёт), иначе пробуем найти по имени
        customer_id = validated_data.get('customer_id')
        if not customer_id:
            customer_val = basic_provisions.get('customer') or validated_data.get('customer_name')
            if isinstance(customer_val, int):
                customer_id = customer_val
            elif isinstance(customer_val, str) and customer_val.strip():
                # Поиск по username или по ФИО
                candidate = (
                    User.objects.filter(username=customer_val).first()
                    or User.objects.filter(first_name__icontains=customer_val.split(' ')[0]).first()
                )
                customer_id = getattr(candidate, 'id', None)

        project = Project.objects.create(
            owner=user,
            status=Project.Status.DRAFT,
            event_block=block_obj,
            event=event_obj,
            short_name=validated_data['short_name'],
            name=validated_data['name'],
            name_clarification=validated_data.get('name_clarification', ''),
            goal=basic_provisions.get('projectGoal', ''),
            start_date=validated_data['start_date'],
            end_date=validated_data['end_date'],
            curator_id=curator_id,
            manager=manager_obj,
            customer_id=customer_id,
            budget_total=to_dec_2(validated_data.get('budget_total')) if validated_data.get('budget_total') is not None else Decimal('0.00'),
            additional_info=(validated_data.get('additional_info') or {}).get('notes', ''),
        )

        # Задачи проекта
        for index, task in enumerate(basic_provisions.get('projectTasks') or []):
            if isinstance(task, str) and task.strip():
                ProjectTask.objects.create(project=project, description=task.strip(), order=index)

        # Планируемые результаты
        for index, res in enumerate(basic_provisions.get('plannedResults') or []):
            if isinstance(res, str) and res.strip():
                ProjectPlannedResult.objects.create(project=project, description=res.strip(), order=index)

        # Исполнители (из basic_provisions.executors ожидается список id пользователей)
        executors = basic_provisions.get('executors') or []
        if isinstance(executors, list):
            for user_id in executors:
                try:
                    ProjectExecutor.objects.create(project=project, user_id=int(user_id))
                except Exception:
                    continue

        # Целевые показатели
        for item in (validated_data.get('target_indicators') or []):
            source_id = item.get('source_indicator_id') or item.get('id')
            name = item.get('name') or item.get('title')
            unit = item.get('unit') or item.get('measurement') or ''
            baseline = item.get('baseline')
            planned = item.get('planned')

            ProjectTargetIndicator.objects.create(
                project=project,
                source_indicator_id=source_id,
                name=name or '',
                unit=unit or '',
                baseline=baseline,
                planned=planned,
            )

        # Этапы и бюджет-этапы
        calendar_plan = validated_data.get('calendar_plan') or {}
        item_stage_map: Dict[str, ProjectStage] = {}
        for idx, st in enumerate(calendar_plan.get('stages') or []):
            stage = ProjectStage.objects.create(
                project=project,
                name=st.get('name') or '',
                start_date=st.get('startDate') or project.start_date,
                end_date=st.get('endDate') or project.end_date,
                planned_results='\n'.join(st.get('plannedResults') or []),
                order=idx,
            )
            key = str(st.get('id') or st.get('key') or idx)
            item_stage_map[key] = stage

        budget_block = validated_data.get('budget') or {}
        for it in budget_block.get('items') or []:
            stage_key = str(it.get('stage') or it.get('stageId') or '')
            ProjectBudgetItem.objects.create(
                project=project,
                stage=item_stage_map.get(stage_key),
                cost_article=it.get('article') or it.get('costArticle') or '',
                funding_source=it.get('source') or it.get('fundingSource') or '',
                amount=to_dec_2(it.get('amount') or 0),
            )

        totals = budget_block.get('totals') or {}
        if totals:
            ProjectBudgetTotal.objects.create(
                project=project,
                total_with_insurance=to_dec_2(totals.get('withInsurance') or 0),
                salary_off_budget=to_dec_2(totals.get('salaryOffBudget') or totals.get('salary') or 0),
                salary_budget=to_dec_2(totals.get('salaryBudget') or 0),
                other_off_budget=to_dec_2(totals.get('otherOffBudget') or 0),
                other_budget=to_dec_2(totals.get('otherBudget') or totals.get('other') or 0),
            )

        # Сохранение версии v1
        snapshot = self._snapshot_payload(validated_data)
        last_version = ProjectVersion.objects.filter(project=project).order_by('-version_number').first()
        next_number = (last_version.version_number + 1) if last_version else 1
        ProjectVersion.objects.create(
            project=project,
            version_number=next_number,
            title=f'Создано {timezone.now().strftime("%Y-%m-%d %H:%M")}',
            payload=snapshot,
            created_by=user if user and user.is_authenticated else None,
        )

        return project


class ProjectUserRoleSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = ProjectUserRole
        fields = ['user_id', 'role', 'role_name']


class ProjectReadSerializer(serializers.ModelSerializer):
    user_role = serializers.SerializerMethodField()
    roles = ProjectUserRoleSerializer(source='user_roles', many=True, read_only=True)
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    customer_id = serializers.IntegerField(source='customer.id', read_only=True)
    
    class Meta:
        model = Project
        fields = (
            'id', 'status', 'short_name', 'name', 'name_clarification', 'goal',
            'start_date', 'end_date', 'event_block_id', 'event_id',
            'owner_id', 'curator_id', 'manager_id', 'customer_id', 'budget_total', 'additional_info',
            'created_at', 'updated_at', 'user_role', 'roles',
        )
    
    def get_user_role(self, obj):
        """Определяет роль текущего пользователя в проекте."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 'Неизвестно'
        
        user = request.user
        
        # Если есть назначенная роль через ProjectUserRole — берём её
        link = obj.user_roles.filter(user=user).select_related('role').first()
        if link and getattr(link, 'role', None):
            return link.role.name or 'Неизвестно'

        # Fallback на поля проекта
        if obj.manager == user:
            return 'Руководитель'
        elif obj.curator == user:
            return 'Куратор'
        elif obj.customer == user:
            return 'Заказчик'
        elif obj.executors.filter(user=user).exists():
            # Получаем роль исполнителя из ProjectExecutor
            executor = obj.executors.filter(user=user).first()
            return executor.role if executor and executor.role else 'Исполнитель'
        
        return 'Неизвестно'