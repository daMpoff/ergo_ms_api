from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.project_ed.models import Project
from src.modules.project_ed.serializers import ProjectSerializer


class ProjectPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner_id == getattr(request.user, 'id', None)
        return obj.owner_id == getattr(request.user, 'id', None)


class ProjectViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = ProjectPagination

    def get_queryset(self):
        base_qs = super().get_queryset()
        user = self.get_safe_user()
        if user is None:
            return self.get_safe_queryset(base_qs)
        return base_qs.filter(owner=user)