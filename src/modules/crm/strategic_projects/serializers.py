from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    DevelopmentProgram, ProgramTopic, StrategicProject,
    ProjectStage, StageExecutor, ProjectReport,
    StageResult, ProjectHistory, UserProjectRole, EmployeeWorkload,
    ProjectNotification
)

User = get_user_model()


class StrategicProjectUserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'first_name', 'last_name']


class ProgramTopicSerializer(serializers.ModelSerializer):
    """Сериализатор для тем программы развития"""
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = ProgramTopic
        fields = '__all__'
        read_only_fields = ['project']
    
    def get_is_available(self, obj):
        return obj.status == 'free'


class DevelopmentProgramSerializer(serializers.ModelSerializer):
    """Сериализатор для программы развития"""
    topics = ProgramTopicSerializer(many=True, read_only=True)
    topics_count = serializers.IntegerField(source='topics.count', read_only=True)
    free_topics_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DevelopmentProgram
        fields = '__all__'
    
    def get_free_topics_count(self, obj):
        return obj.topics.filter(status='free').count()


class StageExecutorSerializer(serializers.ModelSerializer):
    """Сериализатор для исполнителей этапа"""
    user_info = StrategicProjectUserSerializer(source='user', read_only=True)
    
    class Meta:
        model = StageExecutor
        fields = '__all__'


class StageResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов этапа"""
    
    class Meta:
        model = StageResult
        fields = '__all__'


class ProjectStageSerializer(serializers.ModelSerializer):
    """Сериализатор для этапов проекта"""
    executors = StageExecutorSerializer(many=True, read_only=True)
    results = StageResultSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectStage
        fields = '__all__'
        read_only_fields = ['project']
    
    def get_progress(self, obj):
        if obj.status == 'completed':
            return 100
        elif obj.status == 'in_progress':
            return 50
        return 0


class ProjectReportSerializer(serializers.ModelSerializer):
    """Сериализатор для отчетов по проекту"""
    stage_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectReport
        fields = '__all__'
        read_only_fields = ['project']
    
    def get_stage_info(self, obj):
        if obj.stage:
            return {
                'id': obj.stage.id,
                'name': obj.stage.name,
                'order_number': obj.stage.order_number
            }
        return None


class ProjectHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории изменений"""
    user_info = StrategicProjectUserSerializer(source='user', read_only=True)
    
    class Meta:
        model = ProjectHistory
        fields = '__all__'
        read_only_fields = ['project', 'user', 'created_at']


class StrategicProjectSerializer(serializers.ModelSerializer):
    """Сериализатор для стратегических проектов"""
    topic_info = ProgramTopicSerializer(source='topic', read_only=True)
    leader_info = StrategicProjectUserSerializer(source='leader', read_only=True)
    curator_info = StrategicProjectUserSerializer(source='curator', read_only=True)
    customer_info = StrategicProjectUserSerializer(source='customer', read_only=True)
    stages = ProjectStageSerializer(many=True, read_only=True)
    reports = ProjectReportSerializer(many=True, read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = StrategicProject
        fields = '__all__'
        read_only_fields = ['code', 'created_at']
    
    def get_completion_percentage(self, obj):
        total_stages = obj.stages.count()
        if total_stages == 0:
            return 0
        completed_stages = obj.stages.filter(status='completed').count()
        return int((completed_stages / total_stages) * 100)


class StrategicProjectListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка проектов (краткая информация)"""
    leader_name = serializers.CharField(source='leader.get_full_name', read_only=True)
    curator_name = serializers.CharField(source='curator.get_full_name', read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = StrategicProject
        fields = [
            'id', 'code', 'name', 'status', 'leader_name', 
            'curator_name', 'planned_start_date', 'planned_end_date',
            'completion_percentage', 'created_at'
        ]
    
    def get_completion_percentage(self, obj):
        total_stages = obj.stages.count()
        if total_stages == 0:
            return 0
        completed_stages = obj.stages.filter(status='completed').count()
        return int((completed_stages / total_stages) * 100)


class CreateProjectFromTopicSerializer(serializers.Serializer):
    """Сериализатор для создания проекта из темы"""
    topic_id = serializers.IntegerField()
    
    def validate_topic_id(self, value):
        try:
            topic = ProgramTopic.objects.get(id=value)
            if topic.status != 'free':
                raise serializers.ValidationError("Эта тема уже занята")
        except ProgramTopic.DoesNotExist:
            raise serializers.ValidationError("Тема не найдена")
        return value


class ImportProgramSerializer(serializers.Serializer):
    """Сериализатор для импорта программы развития"""
    file = serializers.FileField()
    year = serializers.IntegerField()
    name = serializers.CharField(max_length=255)


class UserProjectRoleSerializer(serializers.ModelSerializer):
    """Сериализатор для ролей пользователей в стратегических проектах"""
    user_info = StrategicProjectUserSerializer(source='user', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    created_by_info = StrategicProjectUserSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = UserProjectRole
        fields = '__all__'
        read_only_fields = ['created_at', 'created_by']


class EmployeeWorkloadSerializer(serializers.ModelSerializer):
    """Сериализатор для загруженности сотрудников"""
    user_info = StrategicProjectUserSerializer(source='user', read_only=True)
    project_info = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeeWorkload
        fields = '__all__'
    
    def get_project_info(self, obj):
        return {
            'id': obj.project.id,
            'code': obj.project.code,
            'name': obj.project.name,
            'status': obj.project.status
        }


class ProjectNotificationSerializer(serializers.ModelSerializer):
    """Сериализатор для уведомлений проектов"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_code = serializers.CharField(source='project.code', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = ProjectNotification
        fields = [
            'id', 
            'project', 
            'project_name',
            'project_code',
            'recipient',
            'recipient_name',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'is_read',
            'created_at',
            'read_at'
        ]
        read_only_fields = ['id', 'created_at'] 