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
    ImpulsMultipleFileUploadSerializer,
    ImpulsAnalysisBulkDownloadSerializer,
    ImpulsAnalysisBulkDeleteSerializer
)
from src.modules.impuls_analysis.tasks import create_analysis_by_protocol, import_impuls_excel

# Получаем логгер для модуля
logger = logging.getLogger('modules.impuls_analysis')


class ImpulsAnalysisPagination(PageNumberPagination):
    """Пагинация для анализов импульса"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ImpulsProtocolPagination(PageNumberPagination):
    """Пагинация для протоколов импульса"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class ImpulsAnalysisViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления анализами импульса
    """
    queryset = ImpulsAnalysis.objects.all()
    serializer_class = ImpulsAnalysisSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ImpulsAnalysisPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['title', 'description', 'protocol_number']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        """Возвращаем все анализы для всех пользователей"""
        return self.queryset.all()

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

    @action(detail=False, methods=['post'])
    def upload_multiple_files(self, request):
        """Загрузка множественных файлов для импорта данных"""
        serializer = ImpulsMultipleFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                task_ids = []
                
                # Обрабатываем файлы расчета силы
                force_files = request.FILES.getlist('force_calculation_files')
                for force_file in force_files:
                    # Сохраняем файл в media директорию
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, force_file.name)
                    with open(file_path, 'wb') as f:
                        for chunk in force_file.chunks():
                            f.write(chunk)
                    
                    # Запускаем импорт данных из файла
                    task = import_impuls_excel.delay(file_path, 'force')
                    task_ids.append(task.id)
                    logger.info(f'Запущен импорт force файла {force_file.name}, задача: {task.id}')

                # Обрабатываем файлы плана эксперимента
                plan_files = request.FILES.getlist('experiment_plan_files')
                for plan_file in plan_files:
                    # Сохраняем файл в media директорию
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, plan_file.name)
                    with open(file_path, 'wb') as f:
                        for chunk in plan_file.chunks():
                            f.write(chunk)
                    
                    # Запускаем импорт данных из файла
                    task = import_impuls_excel.delay(file_path, 'plan')
                    task_ids.append(task.id)
                    logger.info(f'Запущен импорт plan файла {plan_file.name}, задача: {task.id}')

                total_files = len(force_files) + len(plan_files)
                logger.info(f'Запущен импорт {total_files} файлов, задач: {len(task_ids)}')

                return Response({
                    'success': True,
                    'message': f'Загружено {total_files} файлов и запущен импорт',
                    'task_ids': task_ids,
                    'files_processed': {
                        'force_files': len(force_files),
                        'plan_files': len(plan_files)
                    }
                }, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f'Ошибка при загрузке множественных файлов: {str(e)}')
                return Response(
                    {'success': False, 'error': f'Ошибка при загрузке файлов: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=['get'])
    def download_results(self, request, pk=None):
        """Возвращает прямые ссылки на файлы результатов анализа вместо архива."""
        analysis = self.get_object()

        try:
            media_urls = []
            analysis_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'analyses')
            if os.path.exists(analysis_dir):
                for filename in os.listdir(analysis_dir):
                    if filename.startswith(str(analysis.id)):
                        file_path = os.path.join(analysis_dir, filename)
                        if os.path.isfile(file_path):
                            relative_path = os.path.join('impuls_analysis', 'analyses', filename).replace('\\', '/')
                            url_path = settings.MEDIA_URL.rstrip('/') + '/' + relative_path
                            absolute_url = request.build_absolute_uri(url_path)
                            media_urls.append({
                                'filename': filename,
                                'url': absolute_url,
                            })

            # Также вернем краткую текстовую информацию как отдельный файл-контент (опционально)
            analysis_info = {
                'title': analysis.title,
                'description': analysis.description,
                'status': analysis.status,
                'protocol_number': analysis.protocol_number,
                'p_static': analysis.p_static,
                'energy_j': analysis.energy_j,
                'created_at': analysis.created_at,
                'started_at': analysis.started_at,
                'completed_at': analysis.completed_at,
                'error_message': analysis.error_message,
            }

            return Response({
                'files': media_urls,
                'info': analysis_info,
                'count': len(media_urls),
            })
        except Exception as e:
            logger.error(f'Ошибка при формировании ссылок на результаты анализа {analysis.id}: {str(e)}')
            return Response({'error': f'Ошибка при получении результатов: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def bulk_download_protocols(self, request):
        """Массовое скачивание протоколов"""
        serializer = ImpulsAnalysisBulkDownloadSerializer(data=request.data)
        if serializer.is_valid():
            analysis_ids = serializer.validated_data['analysis_ids']
            analyses = ImpulsAnalysis.objects.filter(
                id__in=analysis_ids
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

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """Массовое удаление анализов"""
        serializer = ImpulsAnalysisBulkDeleteSerializer(data=request.data)
        if serializer.is_valid():
            analysis_ids = serializer.validated_data['analysis_ids']
            
            try:
                # Получаем анализы пользователя
                analyses = ImpulsAnalysis.objects.filter(
                    id__in=analysis_ids,
                    user=request.user
                )
                
                deleted_count = 0
                for analysis in analyses:
                    try:
                        analysis.delete()
                        deleted_count += 1
                        logger.info(f'Удален анализ {analysis.id} пользователем {request.user.id}')
                    except Exception as e:
                        logger.error(f'Ошибка при удалении анализа {analysis.id}: {str(e)}')
                
                return Response({
                    'success': True,
                    'message': f'Удалено {deleted_count} из {len(analysis_ids)} анализов',
                    'deleted_count': deleted_count,
                    'total_requested': len(analysis_ids)
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f'Ошибка при массовом удалении анализов: {str(e)}')
                return Response(
                    {'success': False, 'error': f'Ошибка при массовом удалении: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получить статистику всех анализов"""
        all_analyses = ImpulsAnalysis.objects.all()
        
        stats = {
            'total': all_analyses.count(),
            'pending': all_analyses.filter(status='pending').count(),
            'processing': all_analyses.filter(status='processing').count(),
            'completed': all_analyses.filter(status='completed').count(),
            'failed': all_analyses.filter(status='failed').count(),
            'cancelled': all_analyses.filter(status='cancelled').count(),
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def available_protocols(self, request):
        """Получить протоколы, готовые для создания анализа"""
        try:
            # Получаем параметры пагинации
            page_size = int(request.query_params.get('page_size', 1000))  # Увеличиваем лимит по умолчанию
            page = int(request.query_params.get('page', 1))
            
            # Получаем параметры сортировки
            sort_field = request.query_params.get('sort_field', 'protocol_number')
            sort_direction = request.query_params.get('sort_direction', 'asc')
            
            # Ограничиваем размер страницы
            page_size = min(page_size, 1000)  # Максимум 1000 элементов на странице
            
            # Получаем все протоколы из обеих таблиц без ограничений
            force_records = ImpulsForceRecord.objects.values_list('protocol_number', flat=True).distinct()
            plan_records = ImpulsPlanRecord.objects.values_list('protocol_number', flat=True).distinct()
            
            # Преобразуем в списки для обработки
            force_protocols = list(force_records)
            plan_protocols = list(plan_records)
            
            logger.info(f'Найдено {len(force_protocols)} протоколов в force_records и {len(plan_protocols)} в plan_records')
            
            # Находим пересечение - протоколы, которые есть в обеих таблицах
            available_protocols = set(force_protocols) & set(plan_protocols)
            
            logger.info(f'Доступных протоколов для анализа: {len(available_protocols)}')
            
            # Сортируем протоколы согласно параметрам сортировки
            if sort_field == 'protocol_number':
                # Специальная сортировка для номера протокола
                sorted_protocols = sorted(available_protocols, key=lambda x: (int(x) if x.isdigit() else float('inf'), x))
            else:
                # Для других полей нужно получить данные и сортировать по ним
                protocols_with_data = []
                for protocol_number in available_protocols:
                    force_record = ImpulsForceRecord.objects.filter(protocol_number=protocol_number).first()
                    plan_record = ImpulsPlanRecord.objects.filter(protocol_number=protocol_number).first()
                    
                    # Получаем значение для сортировки
                    sort_value = None
                    if sort_field.startswith('force_data.'):
                        field_name = sort_field.split('.')[1]
                        sort_value = getattr(force_record, field_name, None) if force_record else None
                    elif sort_field.startswith('plan_data.'):
                        field_name = sort_field.split('.')[1]
                        sort_value = getattr(plan_record, field_name, None) if plan_record else None
                    
                    protocols_with_data.append({
                        'protocol_number': protocol_number,
                        'sort_value': sort_value if sort_value is not None else float('inf')
                    })
                
                # Сортируем по значению
                sorted_protocols = sorted(protocols_with_data, key=lambda x: x['sort_value'])
                sorted_protocols = [p['protocol_number'] for p in sorted_protocols]
            
            # Применяем направление сортировки
            if sort_direction == 'desc':
                sorted_protocols = sorted_protocols[::-1]
            
            # Применяем пагинацию
            total_count = len(sorted_protocols)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_protocols = sorted_protocols[start_index:end_index]
            
            protocols_data = []
            for protocol_number in paginated_protocols:
                # Получаем данные из обеих таблиц
                force_record = ImpulsForceRecord.objects.filter(protocol_number=protocol_number).first()
                plan_record = ImpulsPlanRecord.objects.filter(protocol_number=protocol_number).first()
                
                # Проверяем, есть ли уже анализы для этого протокола
                existing_analyses = ImpulsAnalysis.objects.filter(
                    protocol_number=protocol_number
                ).order_by('-created_at')
                
                # Получаем информацию о последнем анализе
                latest_analysis = existing_analyses.first() if existing_analyses.exists() else None
                
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
                    },
                    'analysis_info': {
                        'has_analysis': existing_analyses.exists(),
                        'analyses_count': existing_analyses.count(),
                        'latest_analysis': {
                            'id': str(latest_analysis.id) if latest_analysis else None,
                            'title': latest_analysis.title if latest_analysis else None,
                            'status': latest_analysis.status if latest_analysis else None,
                            'created_at': latest_analysis.created_at.isoformat() if latest_analysis else None,
                        } if latest_analysis else None
                    }
                })
            
            # Вычисляем информацию о пагинации
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            logger.info(f'Возвращаем {len(protocols_data)} протоколов (страница {page} из {total_pages})')
            
            return Response({
                'protocols': protocols_data,
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_previous': has_previous,
                'next_page': page + 1 if has_next else None,
                'previous_page': page - 1 if has_previous else None,
                'sort': {
                    'field': sort_field,
                    'direction': sort_direction
                }
            })
            
        except Exception as e:
            logger.error(f'Ошибка при получении доступных протоколов: {str(e)}')
            return Response(
                {'error': f'Ошибка при получении протоколов: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def create_from_protocol(self, request):
        """Создать анализ из готового протокола"""
        protocol_number = request.data.get('protocol_number')
        title = request.data.get('title', f'Анализ протокола {protocol_number}')
        description = request.data.get('description', '')
        
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
                protocol_number=protocol_number,
                p_static=force_record.pct_static,
                energy_j=force_record.energy_j,
                status='processing'
            )
            
            # Запускаем обработку, передавая analysis_id, чтобы сохранить UUID
            task = create_analysis_by_protocol.delay(
                protocol_number,
                request.user.id,
                title,
                description,
                str(analysis.id)
            )
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
                # Если есть протокол, используем create_analysis_by_protocol, сохраняем UUID
                task = create_analysis_by_protocol.delay(
                    analysis.protocol_number,
                    analysis.user.id,
                    analysis.title,
                    analysis.description,
                    str(analysis.id)
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
