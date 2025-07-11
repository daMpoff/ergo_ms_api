from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer
from rest_framework.pagination import PageNumberPagination
from django.http import FileResponse, HttpResponse
import os
import zipfile
import io
import logging

# Настраиваем логгер
logger = logging.getLogger('celery.task.porosity_analysis')

from src.modules.porosity_analysis.models import PorosityAnalysis
from src.modules.porosity_analysis.serializers import (
    PorosityAnalysisSerializer,
    CreatePorosityAnalysisSerializer,
    PorosityAnalysisStatusSerializer,
    PorosityAnalysisResultsSerializer
)
from src.modules.porosity_analysis.tasks import run_porosity_analysis, check_concurrent_analyses_limit
from src.modules.porosity_analysis.utils import save_uploaded_image, get_analysis_results_files, create_analysis_summary
from src.modules.porosity_analysis.config import PorosityAnalysisConfig


class PorosityAnalysisViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления анализами пористости
    """
    serializer_class = PorosityAnalysisSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'created_at']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'porosity_percentage']
    ordering = ['-created_at']
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        """Возвращаем queryset с явной сортировкой для консистентной пагинации"""
        return PorosityAnalysis.objects.all().order_by('-created_at', 'id')
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return CreatePorosityAnalysisSerializer
        elif self.action == 'status':
            return PorosityAnalysisStatusSerializer
        elif self.action == 'results':
            return PorosityAnalysisResultsSerializer
        return PorosityAnalysisSerializer
    
    def list(self, request, *args, **kwargs):
        """Переопределяем метод list для обеспечения пагинации"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Создание анализа (задача запускается только после загрузки изображения)"""
        analysis = serializer.save()
        return analysis
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request, pk=None):
        """Загрузка изображения для анализа"""
        analysis = self.get_object()
        
        if 'image' not in request.FILES:
            return Response({
                'error': 'Файл изображения не найден'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        
        try:
            # Сохраняем изображение
            save_uploaded_image(image_file, analysis.original_image_uuid)
            
            # Убрана проверка лимита одновременных анализов
            
            # Запускаем анализ только после успешной загрузки изображения
            analysis.status = 'pending'
            analysis.error_message = ''
            analysis.save()
            run_porosity_analysis.delay(analysis.id)
            
            return Response({
                'message': 'Изображение загружено успешно, анализ запущен',
                'analysis_id': analysis.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Ошибка при загрузке изображения: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """Перезапуск анализа"""
        try:
            analysis = self.get_object()
            
            # Проверяем, что у анализа есть изображение
            if not analysis.original_image_uuid:
                return Response({
                    'error': 'Невозможно перезапустить анализ без изображения'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем, что изображение существует
            image_path = analysis.original_image_path
            if not image_path or not os.path.exists(image_path):
                return Response({
                    'error': 'Исходное изображение не найдено'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем, что изображение не пустое
            if os.path.getsize(image_path) == 0:
                return Response({
                    'error': 'Исходное изображение пустое'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Очищаем старые результаты если они есть
            if analysis.results_directory and os.path.exists(analysis.results_directory):
                try:
                    import shutil
                    shutil.rmtree(analysis.results_directory)
                    logger.info(f"Удалена старая директория результатов для анализа {analysis.id}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить старую директорию результатов: {e}")
            
            # Удаляем старый архив, если он есть
            zip_path = os.path.join(analysis.results_directory or '', f"analysis_{analysis.id}_results.zip")
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                    logger.info(f"Удален старый архив для анализа {analysis.id}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить старый архив: {e}")
            
            # Сбрасываем статус и ошибки
            analysis.status = 'pending'
            analysis.error_message = ''
            analysis.porosity_percentage = None
            analysis.number_of_pores = None
            analysis.average_pore_size = None
            analysis.max_pore_size = None
            analysis.min_pore_size = None
            analysis.pore_density = None
            analysis.average_interpore_distance = None
            analysis.save()
            
            # Запускаем асинхронную задачу
            run_porosity_analysis.delay(analysis.id)
            
            logger.info(f"Анализ {analysis.id} перезапущен успешно")
            
            return Response({
                'success': True,
                'message': 'Анализ перезапущен',
                'analysis_id': analysis.id,
                'status': 'pending'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка при перезапуске анализа {pk}: {e}")
            return Response({
                'success': False,
                'error': f'Ошибка при перезапуске анализа: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Получение статуса анализа"""
        analysis = self.get_object()
        serializer = self.get_serializer(analysis)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Получение результатов анализа"""
        analysis = self.get_object()
        
        if analysis.status != 'completed':
            return Response({
                'error': 'Анализ еще не завершен',
                'status': analysis.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(analysis)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Получение краткого описания анализа"""
        analysis = self.get_object()
        summary = create_analysis_summary(analysis)
        return Response(summary)
    
    @action(detail=True, methods=['get'])
    def download_results(self, request, pk=None):
        """Скачивание результатов анализа в виде ZIP архива (с кэшированием)"""
        analysis = self.get_object()
        
        if analysis.status != 'completed':
            return Response({
                'error': 'Анализ еще не завершен'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем список файлов результатов
        result_files = get_analysis_results_files(analysis)
        
        if not result_files:
            return Response({
                'error': 'Файлы результатов не найдены'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем, что директория результатов существует
        if not os.path.exists(analysis.results_directory):
            return Response({
                'error': 'Директория результатов не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Путь к архиву
        zip_path = os.path.join(analysis.results_directory, f"analysis_{analysis.id}_results.zip")
        
        try:
            # Если архив уже существует и не пустой, просто отдаем его
            if os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
                logger.info(f"Using cached ZIP archive for analysis {analysis.id}")
                with open(zip_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/zip')
                    response['Content-Disposition'] = f'attachment; filename="analysis_{analysis.id}_results.zip"'
                    return response
            
            # Иначе создаем архив и сохраняем на диск
            logger.info(f"Creating new ZIP archive for analysis {analysis.id}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in result_files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        relative_path = os.path.relpath(file_path, analysis.results_directory)
                        logger.info(f"Adding file to archive: {file_path} -> {relative_path}")
                        zip_file.write(file_path, relative_path)
                    else:
                        logger.warning(f"File not found or not a file: {file_path}")
            
            # Отдаем только что созданный архив
            with open(zip_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="analysis_{analysis.id}_results.zip"'
                return response
                
        except Exception as e:
            logger.error(f"Error creating ZIP archive for analysis {analysis.id}: {e}")
            return Response({
                'error': f'Ошибка при создании архива: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def download_file(self, request, pk=None):
        """Скачивание конкретного файла результатов"""
        analysis = self.get_object()
        file_path = request.query_params.get('file')
        
        if not file_path:
            return Response({
                'error': 'Не указан путь к файлу'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        full_path = os.path.join(analysis.results_directory, file_path)
    
    @action(detail=True, methods=['get'])
    def files_info(self, request, pk=None):
        """Получение информации о файлах результатов"""
        analysis = self.get_object()
        
        print(f"Files info endpoint called for analysis {analysis.id}")
        print(f"Results directory: {analysis.results_directory}")
        print(f"Directory exists: {os.path.exists(analysis.results_directory) if analysis.results_directory else False}")
        
        # Получаем список файлов
        result_files = analysis.get_result_files()
        
        print(f"Found {len(result_files)} result files")
        for file in result_files:
            print(f"  - {file['name']} ({file['size']} bytes)")
        
        # Добавляем отладочную информацию
        debug_info = {
            'results_directory': analysis.results_directory,
            'directory_exists': os.path.exists(analysis.results_directory),
            'files_count': len(result_files),
            'files': result_files
        }
        
        return Response({
            'files': result_files,
            'debug': debug_info
        })
    
    @action(detail=True, methods=['get'])
    def image(self, request, pk=None):
        """Получение изображения результатов"""
        analysis = self.get_object()
        filename = request.query_params.get('file')
        
        print(f"Image endpoint called for analysis {analysis.id}, filename: {filename}")
        
        if not filename:
            return Response({
                'error': 'Не указано имя файла'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file_path = os.path.join(analysis.results_directory, filename)
        print(f"Looking for file: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        print(f"Directory exists: {os.path.exists(analysis.results_directory)}")
        
        if not os.path.exists(file_path):
            return Response({
                'error': f'Файл не найден: {filename}',
                'path': file_path,
                'directory': analysis.results_directory,
                'directory_exists': os.path.exists(analysis.results_directory)
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                print(f"File read successfully, size: {len(file_content)} bytes")
                response = HttpResponse(file_content, content_type='image/png')
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                return response
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return Response({
                'error': f'Ошибка при чтении файла: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Получить ожидающие анализы"""
        queryset = self.get_queryset().filter(status='pending')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def processing(self, request):
        """Получить обрабатываемые анализы"""
        queryset = self.get_queryset().filter(status='processing')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Получить завершенные анализы"""
        queryset = self.get_queryset().filter(status='completed')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Получить анализы с ошибками"""
        queryset = self.get_queryset().filter(status='failed')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получение статистики анализов"""
        queryset = self.get_queryset()
        total = queryset.count()
        pending = queryset.filter(status='pending').count()
        processing = queryset.filter(status='processing').count()
        completed = queryset.filter(status='completed').count()
        failed = queryset.filter(status='failed').count()
        
        return Response({
            'total': total,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'success_rate': (completed / total * 100) if total > 0 else 0
        })
    
    @action(detail=False, methods=['post'])
    def restart_multiple(self, request):
        """Массовый перезапуск анализов"""
        try:
            analysis_ids = request.data.get('analysis_ids', [])
            status_filter = request.data.get('status', None)
            
            if not analysis_ids and not status_filter:
                return Response({
                    'error': 'Необходимо указать ID анализов или статус для фильтрации'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Получаем анализы для перезапуска
            queryset = self.get_queryset()
            if analysis_ids:
                analyses = queryset.filter(id__in=analysis_ids)
            elif status_filter:
                analyses = queryset.filter(status=status_filter)
            else:
                analyses = queryset.none()
            
            if not analyses.exists():
                return Response({
                    'error': 'Не найдено анализов для перезапуска'
                }, status=status.HTTP_404_NOT_FOUND)
            
            restarted_count = 0
            failed_count = 0
            errors = []
            
            for analysis in analyses:
                try:
                    # Проверяем, что у анализа есть изображение
                    if not analysis.original_image_uuid:
                        errors.append(f"Анализ {analysis.id}: нет изображения")
                        failed_count += 1
                        continue
                    
                    # Проверяем, что изображение существует
                    image_path = analysis.original_image_path
                    if not image_path or not os.path.exists(image_path):
                        errors.append(f"Анализ {analysis.id}: изображение не найдено")
                        failed_count += 1
                        continue
                    
                    # Очищаем старые результаты
                    if analysis.results_directory and os.path.exists(analysis.results_directory):
                        try:
                            import shutil
                            shutil.rmtree(analysis.results_directory)
                        except Exception as e:
                            logger.warning(f"Не удалось удалить старую директорию результатов для анализа {analysis.id}: {e}")
                    
                    # Сбрасываем статус и результаты
                    analysis.status = 'pending'
                    analysis.error_message = ''
                    analysis.porosity_percentage = None
                    analysis.number_of_pores = None
                    analysis.average_pore_size = None
                    analysis.max_pore_size = None
                    analysis.min_pore_size = None
                    analysis.pore_density = None
                    analysis.average_interpore_distance = None
                    analysis.save()
                    
                    # Запускаем асинхронную задачу
                    run_porosity_analysis.delay(analysis.id)
                    restarted_count += 1
                    
                except Exception as e:
                    errors.append(f"Анализ {analysis.id}: {str(e)}")
                    failed_count += 1
            
            logger.info(f"Массовый перезапуск завершен: {restarted_count} успешно, {failed_count} с ошибками")
            
            return Response({
                'success': True,
                'message': f'Перезапущено {restarted_count} анализов',
                'restarted_count': restarted_count,
                'failed_count': failed_count,
                'errors': errors if errors else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка при массовом перезапуске: {e}")
            return Response({
                'success': False,
                'error': f'Ошибка при массовом перезапуске: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Убран эндпоинт limits, так как ограничения сняты
    
    @action(detail=True, methods=['get'])
    def generate_report(self, request, pk=None):
        """Генерация отчетов в форматах DOCX и PDF"""
        analysis = self.get_object()
        
        if analysis.status != 'completed':
            return Response({
                'error': 'Анализ еще не завершен',
                'status': analysis.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .report_generator import PorosityReportGenerator
            
            report_generator = PorosityReportGenerator(analysis)
            reports = report_generator.generate_reports()
            
            if not reports:
                return Response({
                    'error': 'Не удалось сгенерировать отчеты'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Возвращаем информацию о созданных отчетах
            report_info = []
            for report_type, path in reports.items():
                filename = os.path.basename(path)
                report_info.append({
                    'type': report_type,
                    'filename': filename,
                    'size': os.path.getsize(path) if os.path.exists(path) else 0
                })
            
            return Response({
                'message': 'Отчеты успешно сгенерированы',
                'reports': report_info
            })
            
        except Exception as e:
            return Response({
                'error': f'Ошибка при генерации отчетов: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def download_report(self, request, pk=None):
        """Скачивание сгенерированного отчета"""
        analysis = self.get_object()
        report_type = request.query_params.get('type', 'pdf')  # По умолчанию PDF
        
        print(f"Download report called for analysis {analysis.id}, type: {report_type}")
        
        if analysis.status != 'completed':
            return Response({
                'error': 'Анализ еще не завершен'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Путь к директории отчетов
        reports_dir = os.path.join(analysis.results_directory, 'reports')
        print(f"Reports directory: {reports_dir}")
        print(f"Directory exists: {os.path.exists(reports_dir)}")
        
        # Если отчеты еще не созданы, создаем их
        if not os.path.exists(reports_dir) or not os.listdir(reports_dir):
            print("Reports directory does not exist or is empty, generating reports...")
            try:
                from .report_generator import PorosityReportGenerator
                report_generator = PorosityReportGenerator(analysis)
                reports = report_generator.generate_reports()
                print(f"Generated reports: {reports}")
                
                # Проверяем, что отчеты действительно созданы
                if not reports:
                    return Response({
                        'error': 'Не удалось сгенерировать отчеты'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                print(f"Error generating reports: {str(e)}")
                return Response({
                    'error': f'Ошибка при генерации отчетов: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Ищем файл отчета
        report_files = []
        if os.path.exists(reports_dir):
            print(f"Scanning directory: {reports_dir}")
            for filename in os.listdir(reports_dir):
                print(f"Found file: {filename}")
                if filename.endswith(f'.{report_type}'):
                    report_files.append(filename)
                    print(f"Added report file: {filename}")
        
        print(f"Found {len(report_files)} report files for type {report_type}")
        
        if not report_files:
            # Попробуем сгенерировать отчеты еще раз
            print("No report files found, trying to generate reports again...")
            try:
                from .report_generator import PorosityReportGenerator
                report_generator = PorosityReportGenerator(analysis)
                reports = report_generator.generate_reports()
                print(f"Regenerated reports: {reports}")
                
                # Проверяем снова
                if os.path.exists(reports_dir):
                    for filename in os.listdir(reports_dir):
                        if filename.endswith(f'.{report_type}'):
                            report_files.append(filename)
                            print(f"Found regenerated report file: {filename}")
            except Exception as e:
                print(f"Error regenerating reports: {str(e)}")
            
            if not report_files:
                return Response({
                    'error': f'Отчет в формате {report_type} не найден и не может быть сгенерирован',
                    'reports_dir': reports_dir,
                    'dir_exists': os.path.exists(reports_dir),
                    'available_files': os.listdir(reports_dir) if os.path.exists(reports_dir) else []
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Берем самый последний файл
        report_files.sort(reverse=True)
        latest_report = report_files[0]
        file_path = os.path.join(reports_dir, latest_report)
        
        print(f"Selected file: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            return Response({
                'error': f'Файл отчета не найден: {file_path}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return Response({
                'error': f'Файл отчета пустой: {file_path}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # Определяем content type
            content_type = {
                'pdf': 'application/pdf',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }.get(report_type, 'application/octet-stream')
            
            print(f"Content type: {content_type}")
            print(f"File size: {file_size} bytes")
            
            # Отправляем файл
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
                response = HttpResponse(file_content, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="porosity_analysis_{analysis.id}_{analysis.created_at.strftime("%Y%m%d")}.{report_type}"'
                response['Content-Length'] = len(file_content)
                return response
            
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return Response({
                'error': f'Ошибка при скачивании отчета: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)