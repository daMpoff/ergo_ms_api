import logging
import os
from pathlib import Path

from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from src.core.utils.mixins import SwaggerSafeMixin
from src.modules.impuls_analysis.models import (
    ImpulsAnalysis, 
    ImpulsFile, 
    ImpulsProtocol,
    ImpulsForceRecord,
    ImpulsPlanRecord
)
from src.modules.impuls_analysis.serializers import (
    ImpulsAnalysisSerializer,
    ImpulsAnalysisCreateSerializer,
    ImpulsAnalysisUpdateSerializer,
    ImpulsFileSerializer,
    ImpulsProtocolSerializer,
    ImpulsFileUploadSerializer,
    ImpulsAnalysisBulkDownloadSerializer
)
from src.modules.impuls_analysis.tasks import create_analysis_by_protocol, import_impuls_excel

# Получаем логгер для модуля
logger = logging.getLogger('modules.impuls_analysis')


class ImpulsAnalysisPagination(PageNumberPagination):
    """Пагинация для анализов импульса"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ImpulsAnalysisViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления анализами импульса
    """
    queryset = ImpulsAnalysis.objects.all()
    serializer_class = ImpulsAnalysisSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ImpulsAnalysisPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'analysis_type']
    search_fields = ['title', 'description', 'protocol_number']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        """Фильтруем анализы по пользователю"""
        return self.queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия"""
        if self.action == 'create':
            return ImpulsAnalysisCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ImpulsAnalysisUpdateSerializer
        return ImpulsAnalysisSerializer

    def perform_create(self, serializer):
        """Создаем анализ для текущего пользователя"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def upload_files(self, request):
        """Загрузка файлов для импорта данных (без привязки к анализу)"""
        serializer = ImpulsFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                task_ids = []
                
                # Обрабатываем файл расчета силы
                if 'force_calculation_file' in request.FILES:
                    force_file = request.FILES['force_calculation_file']
                    
                    # Сохраняем файл в media директорию
                    import os
                    from django.conf import settings
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, force_file.name)
                    with open(file_path, 'wb') as f:
                        for chunk in force_file.chunks():
                            f.write(chunk)
                    
                    # Запускаем импорт данных из файла
                    task = import_impuls_excel.delay(file_path, 'force')
                    task_ids.append(task.id)
                    logger.info(f'Запущен импорт force файла, задача: {task.id}')

                # Обрабатываем файл плана эксперимента
                if 'experiment_plan_file' in request.FILES:
                    plan_file = request.FILES['experiment_plan_file']
                    
                    # Сохраняем файл в media директорию
                    import os
                    from django.conf import settings
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, plan_file.name)
                    with open(file_path, 'wb') as f:
                        for chunk in plan_file.chunks():
                            f.write(chunk)
                    
                    # Запускаем импорт данных из файла
                    task = import_impuls_excel.delay(file_path, 'plan')
                    task_ids.append(task.id)
                    logger.info(f'Запущен импорт plan файла, задача: {task.id}')

                logger.info(f'Запущен импорт файлов, задач: {len(task_ids)}')

                return Response({
                    'message': 'Файлы загружены и импорт запущен',
                    'task_ids': task_ids
                }, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f'Ошибка при загрузке файлов: {str(e)}')
                return Response(
                    {'error': f'Ошибка при загрузке файлов: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def protocols(self, request, pk=None):
        """Получить протоколы анализа"""
        analysis = self.get_object()
        protocols = analysis.protocols.all()
        serializer = ImpulsProtocolSerializer(protocols, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download_protocol(self, request, pk=None):
        """Скачать протокол анализа"""
        analysis = self.get_object()
        protocol_id = request.query_params.get('protocol_id')
        
        if not protocol_id:
            return Response(
                {'error': 'Не указан ID протокола'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            protocol = analysis.protocols.get(id=protocol_id)
            file_path = protocol.protocol_file.path
            
            if os.path.exists(file_path):
                response = FileResponse(
                    open(file_path, 'rb'),
                    as_attachment=True,
                    filename=f"protocol_{analysis.title}_{protocol.generated_at.strftime('%Y%m%d_%H%M%S')}.docx"
                )
                return response
            else:
                return Response(
                    {'error': 'Файл протокола не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except ImpulsProtocol.DoesNotExist:
            return Response(
                {'error': 'Протокол не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f'Ошибка при скачивании протокола {protocol_id}: {str(e)}')
            return Response(
                {'error': f'Ошибка при скачивании протокола: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_download_protocols(self, request):
        """Массовое скачивание протоколов"""
        serializer = ImpulsAnalysisBulkDownloadSerializer(data=request.data)
        if serializer.is_valid():
            analysis_ids = serializer.validated_data['analysis_ids']
            analyses = ImpulsAnalysis.objects.filter(
                id__in=analysis_ids,
                user=request.user
            )
            
            # Здесь можно реализовать создание ZIP архива с протоколами
            # Пока возвращаем список доступных протоколов
            protocols_data = []
            for analysis in analyses:
                for protocol in analysis.protocols.all():
                    protocols_data.append({
                        'analysis_id': str(analysis.id),
                        'analysis_title': analysis.title,
                        'protocol_id': str(protocol.id),
                        'generated_at': protocol.generated_at,
                        'download_url': f'/api/impuls-analysis/analyses/{analysis.id}/download_protocol/?protocol_id={protocol.id}'
                    })
            
            return Response({
                'protocols': protocols_data,
                'count': len(protocols_data)
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получить статистику анализов"""
        user_analyses = ImpulsAnalysis.objects.filter(user=request.user)
        
        stats = {
            'total': user_analyses.count(),
            'pending': user_analyses.filter(status='pending').count(),
            'processing': user_analyses.filter(status='processing').count(),
            'completed': user_analyses.filter(status='completed').count(),
            'failed': user_analyses.filter(status='failed').count(),
            'cancelled': user_analyses.filter(status='cancelled').count(),
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def available_protocols(self, request):
        """Получить протоколы, готовые для создания анализа"""
        # Получаем протоколы, которые заполнены в обеих таблицах
        force_records = ImpulsForceRecord.objects.values_list('protocol_number', flat=True).distinct()
        plan_records = ImpulsPlanRecord.objects.values_list('protocol_number', flat=True).distinct()
        
        # Находим пересечение - протоколы, которые есть в обеих таблицах
        available_protocols = set(force_records) & set(plan_records)
        
        protocols_data = []
        for protocol_number in available_protocols:
            # Получаем данные из обеих таблиц
            force_record = ImpulsForceRecord.objects.filter(protocol_number=protocol_number).first()
            plan_record = ImpulsPlanRecord.objects.filter(protocol_number=protocol_number).first()
            
            protocols_data.append({
                'protocol_number': protocol_number,
                'force_data': {
                    'pct_static': force_record.pct_static if force_record else None,
                    'energy_j': force_record.energy_j if force_record else None,
                    'velocity_ms': force_record.velocity_ms if force_record else None,
                    'force_n': force_record.force_n if force_record else None,
                },
                'plan_data': {
                    'p_static': plan_record.p_static if plan_record else None,
                    'p_static_value': plan_record.p_static_value if plan_record else None,
                    'l1_l2_ratio': plan_record.l1_l2_ratio if plan_record else None,
                    'l1_m': plan_record.l1_m if plan_record else None,
                    'd1_m': plan_record.d1_m if plan_record else None,
                    'm1_kg': plan_record.m1_kg if plan_record else None,
                    'l2_m': plan_record.l2_m if plan_record else None,
                    'd2_m': plan_record.d2_m if plan_record else None,
                    't_s': plan_record.t_s if plan_record else None,
                    'a_j': plan_record.a_j if plan_record else None,
                    'v_ms': plan_record.v_ms if plan_record else None,
                    'c12_kg_s': plan_record.c12_kg_s if plan_record else None,
                    'p_n': plan_record.p_n if plan_record else None,
                }
            })
        
        return Response({
            'protocols': protocols_data,
            'count': len(protocols_data)
        })

    @action(detail=False, methods=['post'])
    def create_from_protocol(self, request):
        """Создать анализ из готового протокола"""
        protocol_number = request.data.get('protocol_number')
        title = request.data.get('title', f'Анализ протокола {protocol_number}')
        description = request.data.get('description', '')
        analysis_type = request.data.get('analysis_type', 'standard')
        
        if not protocol_number:
            return Response(
                {'error': 'Не указан номер протокола'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что протокол доступен
        force_record = ImpulsForceRecord.objects.filter(protocol_number=protocol_number).first()
        plan_record = ImpulsPlanRecord.objects.filter(protocol_number=protocol_number).first()
        
        if not force_record or not plan_record:
            return Response(
                {'error': 'Протокол не найден или не заполнен полностью'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Создаем анализ
            analysis = ImpulsAnalysis.objects.create(
                user=request.user,
                title=title,
                description=description,
                analysis_type=analysis_type,
                protocol_number=protocol_number,
                p_static=force_record.pct_static,
                energy_j=force_record.energy_j,
                status='processing'
            )
            
            # Запускаем обработку
            task = create_analysis_by_protocol.delay(protocol_number, request.user.id, title, description)
            analysis.task_id = task.id
            analysis.save()
            
            logger.info(f'Создан анализ {analysis.id} из протокола {protocol_number}, задача: {task.id}')
            
            serializer = ImpulsAnalysisSerializer(analysis)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f'Ошибка при создании анализа из протокола {protocol_number}: {str(e)}')
            return Response(
                {'error': f'Ошибка при создании анализа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Получить статус анализа"""
        analysis = self.get_object()
        return Response({
            'id': str(analysis.id),
            'status': analysis.status,
            'status_display': analysis.get_status_display(),
            'task_id': analysis.task_id,
            'created_at': analysis.created_at,
            'started_at': analysis.started_at,
            'completed_at': analysis.completed_at,
            'error_message': analysis.error_message
        })

    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """Перезапустить анализ"""
        analysis = self.get_object()
        
        if analysis.status in ['processing']:
            return Response(
                {'error': 'Анализ уже обрабатывается'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Сбрасываем статус
            analysis.status = 'pending'
            analysis.task_id = None
            analysis.started_at = None
            analysis.completed_at = None
            analysis.error_message = ''
            analysis.save()
            
            # Запускаем обработку
            if analysis.protocol_number:
                # Если есть протокол, используем create_analysis_by_protocol
                task = create_analysis_by_protocol.delay(
                    analysis.protocol_number, 
                    analysis.user.id, 
                    analysis.title, 
                    analysis.description
                )
            else:
                # Если нет протокола, просто обновляем статус
                analysis.status = 'pending'
                analysis.save()
                return Response({
                    'message': 'Анализ перезапущен (ожидает загрузки файлов)',
                    'task_id': None
                })
            
            analysis.task_id = task.id
            analysis.status = 'processing'
            analysis.save()
            
            logger.info(f'Перезапущен анализ {analysis.id}, задача: {task.id}')
            
            return Response({
                'message': 'Анализ перезапущен',
                'task_id': task.id
            })
            
        except Exception as e:
            logger.error(f'Ошибка при перезапуске анализа {analysis.id}: {str(e)}')
            return Response(
                {'error': f'Ошибка при перезапуске анализа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
