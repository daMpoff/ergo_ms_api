from rest_framework import serializers
from django.utils import timezone

from .base_serializers import BaseModelSerializer, TimestampedModelSerializer, CourseRelatedMixin
from .models import Subject, Theme, Lesson, Assignment
from .utils import ValidationMixin


class OptimizedCreateUpdateSerializer(BaseModelSerializer, CourseRelatedMixin, ValidationMixin):
    """Оптимизированный базовый сериализатор для создания/обновления"""
    
    def validate(self, attrs):
        # Общие валидации
        if 'start_date' in attrs and 'end_date' in attrs:
            self.validate_date_range(attrs.get('start_date'), attrs.get('end_date'))
        
        if 'max_enrollment' in attrs:
            self.validate_positive_integer(attrs.get('max_enrollment'), 'Максимальное количество записей')
        
        return attrs


class OptimizedSubjectSerializer(OptimizedCreateUpdateSerializer):
    """Оптимизированный сериализатор курса"""
    
    class Meta:
        model = Subject
        exclude = ['teacher', 'creationdate'] if hasattr(Subject, 'teacher') else []
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        validated_data['creationdate'] = timezone.now()
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['lastupdate'] = timezone.now()
        return super().update(instance, validated_data)


class OptimizedThemeSerializer(OptimizedCreateUpdateSerializer):
    """Оптимизированный сериализатор темы"""
    
    class Meta:
        model = Theme
        exclude = ['creationdate'] if hasattr(Theme, 'creationdate') else []
    
    def validate_subject(self, value):
        return self.validate_subject_access(value)
    
    def create(self, validated_data):
        validated_data['creationdate'] = timezone.now()
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['lastupdate'] = timezone.now()
        return super().update(instance, validated_data)


class OptimizedLessonSerializer(OptimizedCreateUpdateSerializer):
    """Оптимизированный сериализатор урока"""
    
    class Meta:
        model = Lesson
        exclude = ['creationdate'] if hasattr(Lesson, 'creationdate') else []
    
    def validate_theme(self, value):
        """Проверить доступ к теме"""
        return self.validate_subject_access(value.subject)
    
    def create(self, validated_data):
        validated_data['creationdate'] = timezone.now()
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['lastupdate'] = timezone.now()
        return super().update(instance, validated_data)


class OptimizedAssignmentSerializer(OptimizedCreateUpdateSerializer):
    """Оптимизированный сериализатор задания"""
    
    class Meta:
        model = Assignment
        exclude = ['creationdate'] if hasattr(Assignment, 'creationdate') else []
    
    def validate_lesson(self, value):
        """Проверить доступ к уроку"""
        return self.validate_subject_access(value.theme.subject)
    
    def validate_max_grade(self, value):
        self.validate_positive_integer(value, 'Максимальная оценка')
        return value
    
    def create(self, validated_data):
        validated_data['creationdate'] = timezone.now()
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['lastupdate'] = timezone.now()
        return super().update(instance, validated_data) 