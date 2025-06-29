from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectMember, Task, TaskComment, TaskAttachment, TimeLog

User = get_user_model()

# Создавайте свои сериализаторы здесь

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Сериализатор участника проекта"""
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    """Сериализатор проекта"""
    owner = UserSerializer(read_only=True)
    manager = UserSerializer(read_only=True)
    manager_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    memberships = ProjectMemberSerializer(many=True, read_only=True)
    task_count = serializers.SerializerMethodField()
    completed_task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'manager', 'manager_id',
            'memberships', 'status', 'priority', 'start_date', 'end_date',
            'created_at', 'updated_at', 'color', 'task_count', 'completed_task_count'
        ]
    
    def get_task_count(self, obj):
        return obj.tasks.count()
    
    def get_completed_task_count(self, obj):
        return obj.tasks.filter(status='done').count()
    
    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    """Сериализатор списка проектов"""
    owner = UserSerializer(read_only=True)
    manager = UserSerializer(read_only=True)
    task_count = serializers.SerializerMethodField()
    completed_task_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'manager', 'status', 'priority',
            'start_date', 'end_date', 'created_at', 'color', 'task_count',
            'completed_task_count', 'progress'
        ]
    
    def get_task_count(self, obj):
        return obj.tasks.count()
    
    def get_completed_task_count(self, obj):
        return obj.tasks.filter(status='done').count()
    
    def get_progress(self, obj):
        total = obj.tasks.count()
        if total == 0:
            return 0
        completed = obj.tasks.filter(status='done').count()
        return round((completed / total) * 100)


class TaskCommentSerializer(serializers.ModelSerializer):
    """Сериализатор комментария к задаче"""
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TaskComment
        fields = ['id', 'content', 'author', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Сериализатор прикрепленного файла"""
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = ['id', 'file', 'filename', 'uploaded_by', 'uploaded_at']
    
    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class TimeLogSerializer(serializers.ModelSerializer):
    """Сериализатор учета времени"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TimeLog
        fields = ['id', 'description', 'hours', 'date', 'user', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор задачи"""
    assignee = UserSerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    project = ProjectListSerializer(read_only=True)
    assignee_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    project_id = serializers.IntegerField(write_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    time_logs = TimeLogSerializer(many=True, read_only=True)
    total_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'project', 'project_id', 'assignee', 'assignee_id',
            'creator', 'status', 'priority', 'start_date', 'due_date', 'completed_at',
            'created_at', 'updated_at', 'estimated_hours', 'actual_hours', 'kanban_order',
            'comments', 'attachments', 'time_logs', 'total_time'
        ]
    
    def get_total_time(self, obj):
        return sum(log.hours for log in obj.time_logs.all())
    
    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)


class TaskListSerializer(serializers.ModelSerializer):
    """Сериализатор списка задач"""
    assignee = UserSerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    project = ProjectListSerializer(read_only=True)
    comment_count = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'project', 'assignee', 'creator',
            'status', 'priority', 'start_date', 'due_date', 'completed_at',
            'created_at', 'updated_at', 'estimated_hours', 'actual_hours',
            'kanban_order', 'comment_count', 'attachment_count'
        ]
    
    def get_comment_count(self, obj):
        return obj.comments.count()
    
    def get_attachment_count(self, obj):
        return obj.attachments.count()


class TaskCalendarSerializer(serializers.ModelSerializer):
    """Сериализатор задач для календаря"""
    assignee = UserSerializer(read_only=True)
    project = ProjectListSerializer(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'project', 'assignee', 'status',
            'priority', 'start_date', 'due_date', 'created_at'
        ]


class TaskKanbanSerializer(serializers.ModelSerializer):
    """Сериализатор задач для канбан доски"""
    assignee = UserSerializer(read_only=True)
    project = ProjectListSerializer(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'project', 'assignee', 'status',
            'priority', 'due_date', 'kanban_order', 'estimated_hours'
        ]