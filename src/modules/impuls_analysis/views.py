"""
Представления для модуля анализа импульса.
API для работы с анализами, файлами и протоколами.
"""

import logging
import os
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from src.core.utils.mixins import SwaggerSafeMixin
from .models import ImpulsAnalysis, ImpulsFile, ImpulsProtocol
from .serializers import (
    ImpulsAnalysisSerializer,
    ImpulsAnalysisCreateSerializer,
    ImpulsAnalysisUpdateSerializer,
    ImpulsFileUploadSerializer,
    ImpulsAnalysisBulkDownloadSerializer,
)
from .tasks import (
    process_excel_files,
    analyze_impuls_data,
    generate_protocol,
    bulk_download_protocols,
)

logger = logging.getLogger('impuls_analysis')


class ImpulsAnalysisViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления анализами импульса
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ImpulsAnalysisSerializer
    
    def get_queryset(self):
        """Возвращает анализы текущего пользователя"""
        return ImpulsAnalysis.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор"""
        if self.action == 'create':
            return ImpulsAnalysisCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ImpulsAnalysisUpdateSerializer
        return ImpulsAnalysisSerializer
    
    def perform_create(self, serializer):
        """Создает анализ и привязывает к пользователю"""
        analysis = serializer.save(user=self.request.user)
        logger.info(f"Создан новый анализ импульса: {analysis.id}")
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_files(self, request, pk=None):
        """
        Загружает Excel файлы для анализа
        
        Args:
            force_calculation_file: Excel файл с расчетом силы
            experiment_plan_file: Excel файл с планом эксперимента
        """
        analysis = self.get_object()
        
        # Проверяем статус анализа
        if analysis.status not in ['pending', 'failed']:
            return Response(
                {'error': 'Файлы можно загружать только для анализов в статусе "Ожидает обработки" или "Ошибка"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ImpulsFileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Удаляем старые файлы если есть
            analysis.files.all().delete()
            
            # Создаем новые файлы
            files_created = []
            
            if 'force_calculation_file' in request.FILES:
                force_file = request.FILES['force_calculation_file']
                ImpulsFile.objects.create(
                    analysis=analysis,
                    file_type='force_calculation',
                    original_filename=force_file.name,
                    file=force_file
                )
                files_created.append('force_calculation')
            
            if 'experiment_plan_file' in request.FILES:
                experiment_file = request.FILES['experiment_plan_file']
                ImpulsFile.objects.create(
                    analysis=analysis,
                    file_type='experiment_plan',
                    original_filename=experiment_file.name,
                    file=experiment_file
                )
                files_created.append('experiment_plan')
            
            # Обновляем статус анализа
            analysis.status = 'pending'
            analysis.save()
            
            # Запускаем задачу обработки файлов
            process_excel_files.delay(str(analysis.id))
            
            logger.info(f"Файлы загружены для анализа {analysis.id}: {files_created}")
            
            return Response({
                'message': 'Файлы успешно загружены',
                'files_created': files_created,
                'analysis_id': str(analysis.id)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке файлов: {str(e)}")
            return Response(
                {'error': 'Ошибка при загрузке файлов'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def regenerate_protocol(self, request, pk=None):
        """Перегенерирует протокол для анализа"""
        analysis = self.get_object()
        
        if analysis.status != 'completed':
            return Response(
                {'error': 'Протокол можно генерировать только для завершенных анализов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Удаляем старые протоколы
            analysis.protocols.all().delete()
            
            # Запускаем задачу генерации протокола
            generate_protocol.delay(str(analysis.id))
            
            logger.info(f"Запущена перегенерация протокола для анализа {analysis.id}")
            
            return Response({
                'message': 'Перегенерация протокола запущена',
                'analysis_id': str(analysis.id)
            })
            
        except Exception as e:
            logger.error(f"Ошибка при перегенерации протокола: {str(e)}")
            return Response(
                {'error': 'Ошибка при перегенерации протокола'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def download_protocol(self, request, pk=None):
        """Скачивает последний протокол анализа"""
        analysis = self.get_object()
        
        # Получаем последний протокол
        protocol = analysis.protocols.order_by('-generated_at').first()
        if not protocol:
            return Response(
                {'error': 'Протокол не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not protocol.protocol_file:
            return Response(
                {'error': 'Файл протокола не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Проверяем существование файла
            if not os.path.exists(protocol.protocol_file.path):
                return Response(
                    {'error': 'Файл протокола не найден на диске'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Возвращаем файл для скачивания
            response = FileResponse(
                open(protocol.protocol_file.path, 'rb'),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(protocol.protocol_file.name)}"'
            
            logger.info(f"Скачан протокол {protocol.id} для анализа {analysis.id}")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании протокола: {str(e)}")
            return Response(
                {'error': 'Ошибка при скачивании протокола'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_download_protocols(self, request):
        """Скачивает протоколы нескольких анализов в виде архива"""
        serializer = ImpulsAnalysisBulkDownloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        analysis_ids = serializer.validated_data['analysis_ids']
        
        # Проверяем права доступа к анализам
        analyses = ImpulsAnalysis.objects.filter(
            id__in=analysis_ids,
            user=request.user
        )
        
        if len(analyses) != len(analysis_ids):
            return Response(
                {'error': 'Некоторые анализы не найдены или недоступны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Запускаем задачу создания архива
            task = bulk_download_protocols.delay(
                [str(aid) for aid in analysis_ids],
                str(request.user.id)
            )
            
            logger.info(f"Запущено создание архива протоколов для {len(analysis_ids)} анализов")
            
            return Response({
                'message': 'Создание архива запущено',
                'task_id': task.id,
                'analyses_count': len(analysis_ids)
            })
            
        except Exception as e:
            logger.error(f"Ошибка при создании архива: {str(e)}")
            return Response(
                {'error': 'Ошибка при создании архива'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def download_archive(self, request):
        """Скачивает готовый архив протоколов"""
        # Получаем последний созданный архив для пользователя
        archive_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'archives')
        
        if not os.path.exists(archive_dir):
            return Response(
                {'error': 'Архивы не найдены'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ищем последний архив
        archives = [f for f in os.listdir(archive_dir) if f.endswith('.zip')]
        if not archives:
            return Response(
                {'error': 'Архивы не найдены'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Берем самый новый архив
        latest_archive = max(archives, key=lambda x: os.path.getctime(os.path.join(archive_dir, x)))
        archive_path = os.path.join(archive_dir, latest_archive)
        
        try:
            response = FileResponse(
                open(archive_path, 'rb'),
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{latest_archive}"'
            
            logger.info(f"Скачан архив протоколов: {latest_archive}")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании архива: {str(e)}")
            return Response(
                {'error': 'Ошибка при скачивании архива'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Возвращает статистику по анализам пользователя"""
        user_analyses = self.get_queryset()
        
        stats = {
            'total_analyses': user_analyses.count(),
            'completed_analyses': user_analyses.filter(status='completed').count(),
            'pending_analyses': user_analyses.filter(status='pending').count(),
            'processing_analyses': user_analyses.filter(status='processing').count(),
            'failed_analyses': user_analyses.filter(status='failed').count(),
            'total_files': ImpulsFile.objects.filter(analysis__user=request.user).count(),
            'total_protocols': ImpulsProtocol.objects.filter(analysis__user=request.user).count(),
        }
        
        return Response(stats)


class ImpulsFileViewSet(SwaggerSafeMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    ViewSet для управления файлами анализа импульса
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ImpulsAnalysisSerializer
    
    def get_queryset(self):
        """Возвращает файлы анализов текущего пользователя"""
        return ImpulsFile.objects.filter(analysis__user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Удаляет файл и обновляет статус анализа"""
        file_obj = self.get_object()
        analysis = file_obj.analysis
        
        # Удаляем файл
        response = super().destroy(request, *args, **kwargs)
        
        # Обновляем статус анализа если нет файлов
        if not analysis.files.exists():
            analysis.status = 'pending'
            analysis.save()
            logger.info(f"Статус анализа {analysis.id} обновлен на 'pending' после удаления файлов")
        
        return response


class ImpulsProtocolViewSet(SwaggerSafeMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    ViewSet для управления протоколами анализа импульса
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ImpulsAnalysisSerializer
    
    def get_queryset(self):
        """Возвращает протоколы анализов текущего пользователя"""
        return ImpulsProtocol.objects.filter(analysis__user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Скачивает протокол"""
        protocol = self.get_object()
        
        if not protocol.protocol_file:
            return Response(
                {'error': 'Файл протокола не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Проверяем существование файла
            if not os.path.exists(protocol.protocol_file.path):
                return Response(
                    {'error': 'Файл протокола не найден на диске'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Возвращаем файл для скачивания
            response = FileResponse(
                open(protocol.protocol_file.path, 'rb'),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(protocol.protocol_file.name)}"'
            
            logger.info(f"Скачан протокол {protocol.id}")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании протокола: {str(e)}")
            return Response(
                {'error': 'Ошибка при скачивании протокола'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
