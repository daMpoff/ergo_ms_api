from rest_framework import serializers
from .models import Project, Section, Task, Calendar
from django.contrib.auth import get_user_model
from django.conf import settings
from django.apps import apps

# Создавайте свои сериализаторы здесь

User = get_user_model()

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = '__all__'

class CRMUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

# User_Project нет в models.py, поэтому определим вручную
User_Project = apps.get_model('crm', 'User_Project')

class UserProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = User_Project
        fields = '__all__'