from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.core.files.base import ContentFile
import os
import tempfile
import threading
import shutil
from PIL import Image
import numpy as np

from src.external.analysis_porosity.models import PorosityAnalysis, PorosityResult, AnalysisFile
from src.external.analysis_porosity.serializers import (
    PorosityAnalysisListSerializer,
    PorosityAnalysisDetailSerializer,
    PorosityAnalysisCreateSerializer,
    PorosityAnalysisUpdateSerializer,
    BatchAnalysisCreateSerializer,
    BatchAnalysisStatusSerializer
)
from src.external.analysis_porosity.square_porosity.porosity_analyzer import PorosityAnalyzer


class PorosityAnalysisService:
    """Сервис для работы с анализом пористости"""
    
    @staticmethod
    def run_analysis_background(analysis_id):
        """Запускает анализ в фоновом режиме"""
        def process_analysis():
            try:
                analysis = PorosityAnalysis.objects.get(id=analysis_id)
                analysis.status = 'processing'
                analysis.save()
                
                from django.conf import settings  # локальный импорт, чтобы избежать проблем при миграциях
                
                # Создаем директорию в MEDIA_ROOT для обработки результатов
                output_dir = os.path.join(settings.MEDIA_ROOT, 'porosity_analysis', str(analysis_id))
                os.makedirs(output_dir, exist_ok=True)
                
                # Копируем исходное изображение в рабочую директорию
                image_path = os.path.join(output_dir, 'image.png')
                
                # Конвертируем и сохраняем изображение
                with Image.open(analysis.original_image.path) as img:
                    # Конвертируем в RGB если необходимо
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(image_path, 'PNG')
                
                # Запускаем анализ
                analyzer = PorosityAnalyzer()
                results = analyzer.integrated_analysis(
                    image_path,
                    analysis.scale_value,
                    output_dir
                )
                
                if results:
                    # Сохраняем результаты в базу данных
                    PorosityAnalysisService._save_results(analysis, results, output_dir)
                    
                    analysis.status = 'completed'
                    analysis.processed_at = timezone.now()
                    analysis.error_message = ''
                else:
                    analysis.status = 'error'
                    analysis.error_message = 'Ошибка при выполнении анализа'
                    
                analysis.save()
                
            except Exception as e:
                try:
                    analysis = PorosityAnalysis.objects.get(id=analysis_id)
                    analysis.status = 'error'
                    analysis.error_message = str(e)
                    analysis.save()
                except:
                    pass
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=process_analysis)
        thread.daemon = True
        thread.start()
    
    @staticmethod
    def _save_results(analysis, results, output_dir):
        """Сохраняет результаты анализа в базу данных"""
        # Создаем запись результатов
        scale_region = results.get('scale_region', (0, 0, 0, 0))
        
        # Безопасные преобразования массивов (на случай если пришёл обычный list)
        gray_array = np.array(results.get('gray', []))

        # Маски исключённых областей могут прийти в виде list, поэтому конвертируем в bool-массивы numpy
        scale_exclude_mask = np.array(results.get('scale_exclude_mask', []), dtype=bool)
        lines_exclude_mask = np.array(results.get('lines_exclude_mask', []), dtype=bool)
        anomalies_exclude_mask = np.array(results.get('anomalies_exclude_mask', []), dtype=bool)
        exclude_mask = np.array(results.get('exclude_mask', []), dtype=bool)

        # Рассчитываем метрики с использованием numpy, но с защитой от пустых массивов
        total_pixels = int(gray_array.size)
        scale_excluded_pixels = int(np.sum(~scale_exclude_mask)) if scale_exclude_mask.size else 0
        lines_excluded_pixels = int(np.sum(~lines_exclude_mask)) if lines_exclude_mask.size else 0
        anomalies_excluded_pixels = int(np.sum(~anomalies_exclude_mask)) if anomalies_exclude_mask.size else 0
        total_excluded_pixels = int(np.sum(~exclude_mask)) if exclude_mask.size else 0

        result = PorosityResult.objects.create(
            analysis=analysis,
            porosity_percentage=results.get('porosity_percentage', 0),
            relative_pore_area=results.get('relative_pore_area', 0),
            number_of_pores=results.get('number_of_pores', 0),
            mean_pore_size_microns=results.get('mean_pore_size_microns', 0),
            median_pore_size_microns=results.get('median_pore_size_microns', 0),
            mean_pore_diameter_microns=results.get('mean_pore_diameter_microns', 0),
            median_pore_diameter_microns=results.get('median_pore_diameter_microns', 0),
            pixels_per_micron=results.get('pixels_per_micron', 0),
            scale_region_x=scale_region[0],
            scale_region_y=scale_region[1],
            scale_region_width=scale_region[2],
            scale_region_height=scale_region[3],
            total_pixels=total_pixels,
            scale_excluded_pixels=scale_excluded_pixels,
            lines_excluded_pixels=lines_excluded_pixels,
            anomalies_excluded_pixels=anomalies_excluded_pixels,
            total_excluded_pixels=total_excluded_pixels,
            extended_metrics={
                'pore_size_distribution': results.get('pore_size_distribution', {}),
                'interpore_distances': results.get('interpore_distances', {}),
                'pore_orientation': results.get('pore_orientation', {}),
                'pore_shapes': results.get('pore_shapes', {})
            }
        )
        
        # Сохраняем файлы результатов
        file_mappings = {
            'image_with_scale_bar.png': 'scale_bar',
            'scale_bar.png': 'scale_region',
            'figure1_contrast.png': 'contrast_stages',
            'figure2_excluded_areas.png': 'excluded_areas',
            'figure3_texture_clusters.png': 'texture_clusters',
            'figure4_mask_result.png': 'mask_result',
            'figure5_overlay.png': 'overlay',
            'pore_size_distribution.png': 'pore_size_distribution',
            'interpore_distances.png': 'interpore_distances',
            'pore_orientation_rose.png': 'pore_orientation_rose',
            'pore_orientation_histogram.png': 'pore_orientation_histogram',
            'pore_shapes_analysis.png': 'pore_shapes_analysis',
            'circularity_distribution.png': 'circularity_distribution',
            'ellipticity_vs_area.png': 'ellipticity_vs_area',
        }
        
        for filename, file_type in file_mappings.items():
            file_path = os.path.join(output_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    
                analysis_file = AnalysisFile.objects.create(
                    analysis=analysis,
                    file_type=file_type,
                    filename=filename
                )
                
                analysis_file.file.save(
                    f"{analysis.id}_{filename}",
                    ContentFile(file_content),
                    save=True
                )


class PorosityAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с анализами пористости"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Возвращает анализы текущего пользователя"""
        return PorosityAnalysis.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор"""
        if self.action == 'list':
            return PorosityAnalysisListSerializer
        elif self.action == 'create':
            return PorosityAnalysisCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PorosityAnalysisUpdateSerializer
        else:
            return PorosityAnalysisDetailSerializer
    
    def perform_create(self, serializer):
        """Создает новый анализ и автоматически запускает обработку"""
        analysis = serializer.save()
        
        # Автоматически запускаем анализ
        PorosityAnalysisService.run_analysis_background(analysis.id)
        
        return analysis
    
    @action(detail=True, methods=['post'])
    def start_analysis(self, request, pk=None):
        """Запускает анализ пористости"""
        analysis = self.get_object()
        
        if analysis.status == 'processing':
            return Response(
                {'error': 'Анализ уже выполняется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if analysis.status == 'completed':
            return Response(
                {'error': 'Анализ уже завершен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Запускаем анализ
        PorosityAnalysisService.run_analysis_background(analysis.id)
        
        return Response({
            'message': 'Анализ запущен',
            'analysis_id': analysis.id
        })
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Возвращает статус анализа"""
        analysis = self.get_object()
        
        return Response({
            'id': analysis.id,
            'status': analysis.status,
            'status_display': analysis.get_status_display(),
            'error_message': analysis.error_message,
            'created_at': analysis.created_at,
            'processed_at': analysis.processed_at,
            'has_result': hasattr(analysis, 'result')
        })
    
    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """Возвращает результаты анализа"""
        analysis = self.get_object()
        
        if not hasattr(analysis, 'result'):
            return Response(
                {'error': 'Результаты анализа не найдены'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PorosityAnalysisDetailSerializer(analysis, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Возвращает файлы результатов анализа"""
        analysis = self.get_object()
        files = analysis.files.all()
        
        files_data = []
        for file_obj in files:
            file_url = request.build_absolute_uri(file_obj.file.url) if file_obj.file else None
            files_data.append({
                'id': file_obj.id,
                'file_type': file_obj.file_type,
                'file_type_display': file_obj.get_file_type_display(),
                'filename': file_obj.filename,
                'description': file_obj.description,
                'file_url': file_url,
                'created_at': file_obj.created_at
            })
        
        return Response({'files': files_data})
    
    def destroy(self, request, *args, **kwargs):
        """Удаляет анализ (только если он не обрабатывается)"""
        analysis = self.get_object()
        
        if analysis.status == 'processing':
            return Response(
                {'error': 'Нельзя удалить обрабатываемый анализ'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """Создает пакет анализов из нескольких изображений"""
        serializer = BatchAnalysisCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                created_analyses = serializer.save()
                
                # Запускаем анализ для каждого созданного объекта
                for analysis in created_analyses:
                    PorosityAnalysisService.run_analysis_background(analysis.id)
                
                # Возвращаем список созданных анализов
                response_data = []
                for analysis in created_analyses:
                    analysis_serializer = PorosityAnalysisListSerializer(
                        analysis, context={'request': request}
                    )
                    response_data.append(analysis_serializer.data)
                
                return Response({
                    'message': f'Создано {len(created_analyses)} анализов и запущена обработка',
                    'analyses': response_data,
                    'count': len(created_analyses)
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': f'Ошибка создания пакета анализов: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def batch_status(self, request):
        """Возвращает общий статус всех анализов пользователя"""
        analyses = self.get_queryset()
        
        # Подсчитываем статусы
        total_count = analyses.count()
        pending_count = analyses.filter(status='pending').count()
        processing_count = analyses.filter(status='processing').count()
        completed_count = analyses.filter(status='completed').count()
        error_count = analyses.filter(status='error').count()
        
        # Получаем последние анализы
        recent_analyses = analyses.order_by('-created_at')[:10]
        
        # Формируем ответ
        data = {
            'total_count': total_count,
            'pending_count': pending_count,
            'processing_count': processing_count,
            'completed_count': completed_count,
            'error_count': error_count,
            'analyses': PorosityAnalysisListSerializer(
                recent_analyses, many=True, context={'request': request}
            ).data
        }
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def start_all_pending(self, request):
        """Запускает все ожидающие анализы"""
        pending_analyses = self.get_queryset().filter(status='pending')
        
        if not pending_analyses.exists():
            return Response({
                'message': 'Нет ожидающих анализов для запуска'
            })
        
        count = 0
        for analysis in pending_analyses:
            try:
                PorosityAnalysisService.run_analysis_background(analysis.id)
                count += 1
            except Exception as e:
                print(f"Ошибка запуска анализа {analysis.id}: {e}")
        
        return Response({
            'message': f'Запущено {count} анализов из {pending_analyses.count()}',
            'started_count': count,
            'total_pending': pending_analyses.count()
        })
    
    @action(detail=False, methods=['post'])
    def delete_all_failed(self, request):
        """Удаляет все неудачные анализы"""
        failed_analyses = self.get_queryset().filter(status='error')
        count = failed_analyses.count()
        
        if count == 0:
            return Response({
                'message': 'Нет неудачных анализов для удаления'
            })
        
        failed_analyses.delete()
        
        return Response({
            'message': f'Удалено {count} неудачных анализов',
            'deleted_count': count
        })