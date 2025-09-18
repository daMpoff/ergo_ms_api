from rest_framework import serializers

from src.modules.project_ed.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id',
            'owner',
            'short_name',
            'name',
            'name_clarification',
            'start_date',
            'end_date',
            'curator_id',
            'customer_name',
            'manager_name',
            'budget_total',
            'event',
            'basic_provisions',
            'target_indicators',
            'calendar_plan',
            'budget',
            'additional_info',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['owner', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        start = attrs.get('start_date') or getattr(self.instance, 'start_date', None)
        end = attrs.get('end_date') or getattr(self.instance, 'end_date', None)
        if start and end and start >= end:
            raise serializers.ValidationError('Дата начала должна быть раньше даты окончания')
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return super().create(validated_data)