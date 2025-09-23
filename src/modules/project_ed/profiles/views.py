from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import get_object_or_404

from src.core.utils.mixins import SwaggerSafeMixin
from .models import UserProfile
from .serializers import (
    UserDetailSerializer, 
    UserListSerializer, 
    UserProfileSerializer
)

User = get_user_model()


class UserProfileViewSet(SwaggerSafeMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра профилей пользователей."""
    
    queryset = User.objects.select_related(
        'project_ed_profile__role_ref',
        'project_ed_profile__position_ref', 
        'project_ed_profile__faculty_ref',
        'project_ed_profile__department_ref'
    ).all()
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer
    
    def get_queryset(self):
        """Фильтрация пользователей."""
        queryset = super().get_queryset()
        
        # Фильтрация по поиску
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search)
            )
        
        # Фильтрация по роли
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(
                project_ed_profile__role_ref__name__icontains=role
            )
        
        # Фильтрация по факультету
        faculty = self.request.query_params.get('faculty')
        if faculty:
            queryset = queryset.filter(
                project_ed_profile__faculty_ref__name__icontains=faculty
            )
        
        # Фильтрация по кафедре
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(
                project_ed_profile__department_ref__name__icontains=department
            )
        
        # Только публичные профили
        queryset = queryset.filter(
            models.Q(project_ed_profile__isnull=True) |  # Если нет профиля, считаем публичным
            models.Q(project_ed_profile__is_public=True)
        )
        
        return queryset.order_by('first_name', 'last_name')
    
    @action(detail=True, methods=['get'])
    def projects(self, request, pk=None):
        """Получить проекты пользователя."""
        user = self.get_object()
        projects = user.project_ed_projects.all()
        
        # Сериализуем проекты (можно создать отдельный сериализатор)
        projects_data = []
        for project in projects:
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'short_name': project.short_name,
                'status': project.status,
                'start_date': project.start_date,
                'end_date': project.end_date,
                'created_at': project.created_at,
            })
        
        return Response(projects_data)
    


class UserProfileSettingsViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления настройками профиля пользователя."""
    
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def _is_project_ed_admin(self, user):
        """Проверка: является ли пользователь администратором ProjectEd по роли профиля."""
        profile = getattr(user, 'project_ed_profile', None)
        try:
            role_name = getattr(profile, 'role_name', None)
        except Exception:
            role_name = None
        return bool(role_name == 'Администратор') or bool(getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False))
    
    def get_queryset(self):
        """ProjectEd-админы видят все профили, остальные — только свой."""
        user = self.request.user
        if self._is_project_ed_admin(user):
            return self.queryset
        return self.queryset.filter(user=user)
    
    def perform_create(self, serializer):
        """Upsert-поведение с поддержкой ProjectEd-админа: можно указать иного пользователя."""
        request_user = self.request.user
        target_user = serializer.validated_data.get('user') if self._is_project_ed_admin(request_user) else request_user
        if target_user is None:
            target_user = request_user

        profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'user': target_user})
        for field in ['role_ref', 'position_ref', 'faculty_ref', 'department_ref', 'is_public', 'show_email']:
            if field in serializer.validated_data:
                setattr(profile, field, serializer.validated_data[field])
        profile.save()
        serializer.instance = profile
    
    def get_object(self):
        """ProjectEd-админ получает по pk; обычный пользователь — свой профиль."""
        user = self.request.user
        if self._is_project_ed_admin(user):
            return super().get_object()
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'user': user})
        return profile

