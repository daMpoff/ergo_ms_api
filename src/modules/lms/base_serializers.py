from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone


class LMSUserSerializer(serializers.ModelSerializer):
    """Единый сериализатор для пользователей LMS"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'date_joined']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class BaseModelSerializer(serializers.ModelSerializer):
    """Базовый сериализатор с общими методами валидации"""
    
    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError('Название должно содержать минимум 2 символа')
        if len(value) > 200:
            raise serializers.ValidationError('Название не может быть длиннее 200 символов')
        return value.strip()
    
    def validate_description(self, value):
        if value and len(value) > 5000:
            raise serializers.ValidationError('Описание не может быть длиннее 5000 символов')
        return value.strip() if value else ''


class TimestampedModelSerializer(BaseModelSerializer):
    """Сериализатор для моделей с временными метками"""
    
    def create(self, validated_data):
        validated_data['created_at'] = timezone.now()
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['updated_at'] = timezone.now()
        return super().update(instance, validated_data)


class CourseRelatedMixin:
    """Миксин для сериализаторов, связанных с курсами"""
    
    def validate_subject_access(self, subject):
        """Проверить доступ к курсу"""
        user = self.context['request'].user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return subject
        elif 'teacher' in user_roles and subject.teacher == user:
            return subject
        elif subject.is_published:
            return subject
        else:
            raise serializers.ValidationError('У вас нет доступа к этому курсу')


class CountMixin:
    """Миксин для добавления подсчета связанных объектов"""
    
    def get_count_field(self, obj, related_name, filter_kwargs=None):
        """Универсальный метод для подсчета связанных объектов"""
        related_manager = getattr(obj, related_name)
        if filter_kwargs:
            return related_manager.filter(**filter_kwargs).count()
        return related_manager.count() 