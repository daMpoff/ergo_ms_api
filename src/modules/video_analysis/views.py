import logging
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.video_analysis.models import VideoAnalysis
from src.modules.video_analysis.serializers import VideoAnalysisSerializer

# Получаем логгер для модуля
logger = logging.getLogger('video_analysis')

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
        user = self.get_safe_user()
        logger.debug(f"Получение queryset для пользователя {user.username} (ID: {user.id})")
        return self.get_safe_queryset(base_queryset.filter(user=user))
    
    def list(self, request, *args, **kwargs):
        logger.info(f"Запрос списка анализов от пользователя {request.user.username} (ID: {request.user.id})")
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        analysis_id = kwargs.get('pk')
        logger.info(f"Запрос анализа {analysis_id} от пользователя {request.user.username} (ID: {request.user.id})")
        return super().retrieve(request, *args, **kwargs) 