from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.video_analysis.models import VideoAnalysis
from src.modules.video_analysis.serializers import VideoAnalysisSerializer

class VideoAnalysisViewSet(SwaggerSafeMixin, viewsets.ReadOnlyModelViewSet):
    """
    Только просмотр анализов текущего пользователя (list/retrieve)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = VideoAnalysisSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'created_at']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'title', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        base_queryset = VideoAnalysis.objects.all()
        return self.get_safe_queryset(base_queryset.filter(user=self.get_safe_user())) 