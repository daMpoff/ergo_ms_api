from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer
from django.http import FileResponse, HttpResponse
import os
import zipfile
import io

from src.external.analysis_porosity.models import PorosityAnalysis
from src.external.analysis_porosity.serializers import (
    PorosityAnalysisSerializer,
    CreatePorosityAnalysisSerializer,
    PorosityAnalysisStatusSerializer,
    PorosityAnalysisResultsSerializer
)
from src.external.analysis_porosity.tasks import run_porosity_analysis, check_concurrent_analyses_limit
from src.external.analysis_porosity.utils import save_uploaded_image, get_analysis_results_files, create_analysis_summary
from src.external.analysis_porosity.config import PorosityAnalysisConfig


class PorosityAnalysisViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления анализами пористости
    """
    queryset = PorosityAnalysis.objects.all()
    serializer_class = PorosityAnalysisSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'created_at']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'porosity_percentage']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return CreatePorosityAnalysisSerializer
        elif self.action == 'status':
            return PorosityAnalysisStatusSerializer
        elif self.action == 'results':
            return PorosityAnalysisResultsSerializer
        return PorosityAnalysisSerializer
    
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
            
            # Проверяем лимит одновременных анализов
            if not check_concurrent_analyses_limit():
                max_concurrent = PorosityAnalysisConfig.get_max_concurrent_analyses()
                current_processing = PorosityAnalysis.objects.filter(status='processing').count()
                
                return Response({
                    'error': f'Достигнут лимит одновременных анализов ({current_processing}/{max_concurrent}). Попробуйте позже.',
                    'current_processing': current_processing,
                    'max_concurrent': max_concurrent
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
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
        analysis = self.get_object()
        
        # Проверяем лимит одновременных анализов
        if not check_concurrent_analyses_limit():
            max_concurrent = PorosityAnalysisConfig.get_max_concurrent_analyses()
            current_processing = PorosityAnalysis.objects.filter(status='processing').count()
            
            return Response({
                'error': f'Достигнут лимит одновременных анализов ({current_processing}/{max_concurrent}). Попробуйте позже.',
                'current_processing': current_processing,
                'max_concurrent': max_concurrent
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Сбрасываем статус и ошибки
        analysis.status = 'pending'
        analysis.error_message = ''
        analysis.save()
        
        # Запускаем асинхронную задачу
        run_porosity_analysis.delay(analysis.id)
        
        return Response({
            'message': 'Анализ перезапущен',
            'analysis_id': analysis.id
        }, status=status.HTTP_200_OK)
    
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
        """Скачивание результатов анализа в виде ZIP архива"""
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
        
        try:
            # Добавляем отладочную информацию
            print(f"Creating ZIP archive for analysis {analysis.id}")
            print(f"Results directory: {analysis.results_directory}")
            print(f"Number of files to archive: {len(result_files)}")
            
            # Создаем ZIP архив в памяти
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in result_files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        # Добавляем файл в архив с относительным путем
                        relative_path = os.path.relpath(file_path, analysis.results_directory)
                        print(f"Adding file to archive: {file_path} -> {relative_path}")
                        zip_file.write(file_path, relative_path)
                    else:
                        print(f"File not found or not a file: {file_path}")
            
            # Перемещаем указатель в начало буфера
            zip_buffer.seek(0)
            
            # Создаем HTTP ответ с ZIP архивом
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="analysis_{analysis.id}_results.zip"'
            
            return response
            
        except Exception as e:
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
        """Получение списка ожидающих анализов"""
        pending_analyses = self.queryset.filter(status='pending')
        serializer = PorosityAnalysisStatusSerializer(pending_analyses, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def processing(self, request):
        """Получение списка обрабатываемых анализов"""
        processing_analyses = self.queryset.filter(status='processing')
        serializer = PorosityAnalysisStatusSerializer(processing_analyses, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Получение списка завершенных анализов"""
        completed_analyses = self.queryset.filter(status='completed')
        serializer = PorosityAnalysisResultsSerializer(completed_analyses, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Получение списка неудачных анализов"""
        failed_analyses = self.queryset.filter(status='failed')
        serializer = PorosityAnalysisStatusSerializer(failed_analyses, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получение статистики анализов"""
        total = self.queryset.count()
        pending = self.queryset.filter(status='pending').count()
        processing = self.queryset.filter(status='processing').count()
        completed = self.queryset.filter(status='completed').count()
        failed = self.queryset.filter(status='failed').count()
        
        return Response({
            'total': total,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'success_rate': (completed / total * 100) if total > 0 else 0
        })
    
    @action(detail=False, methods=['get'])
    def limits(self, request):
        """Получение информации о лимитах и текущем состоянии"""
        max_concurrent = PorosityAnalysisConfig.get_max_concurrent_analyses()
        current_processing = PorosityAnalysis.objects.filter(status='processing').count()
        can_start_new = check_concurrent_analyses_limit()
        
        return Response({
            'max_concurrent_analyses': max_concurrent,
            'current_processing': current_processing,
            'can_start_new': can_start_new,
            'available_slots': max(0, max_concurrent - current_processing)
        })