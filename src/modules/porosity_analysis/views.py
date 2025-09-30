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
from django.utils import timezone
import os
import zipfile
import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

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
from src.modules.porosity_analysis.utils import save_uploaded_image, get_analysis_results_files, create_analysis_summary, set_cancel_flag
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

    @action(detail=True, methods=['get'])
    def download_original(self, request, pk=None):
        """Скачать исходное изображение анализа (PNG)."""
        analysis = self.get_object()
        file_path = analysis.original_image_path

        if not file_path or not os.path.exists(file_path):
            return Response({
                'error': 'Исходное изображение не найдено'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            filename = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                file_content = f.read()
                response = HttpResponse(file_content, content_type='image/png')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            return Response({
                'error': f'Ошибка при чтении файла: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def delete_multiple(self, request):
        """Массовое удаление анализов по списку ID или строке номеров.

        Тело запроса может содержать:
        - analysis_ids | ids: массив чисел
        - input | ids_text: строка с номерами через запятую/пробел/точку с запятой
        - dry_run: булево; если true, возвратить информацию о том, сколько будет удалено, без фактического удаления
        """
        try:
            ids = request.data.get('analysis_ids') or request.data.get('ids')
            input_text = request.data.get('input') or request.data.get('ids_text') or ''
            dry_run = bool(request.data.get('dry_run'))

            parsed_ids = []
            if isinstance(ids, list):
                parsed_ids.extend([int(x) for x in ids if str(x).isdigit()])
            if isinstance(input_text, str) and input_text.strip():
                import re
                for token in re.split(r"[\s,;]+", input_text.strip()):
                    if token.isdigit():
                        parsed_ids.append(int(token))

            # Удаляем дубликаты
            parsed_ids = list(sorted(set(parsed_ids)))

            if not parsed_ids:
                return Response({
                    'success': False,
                    'error': 'Не указаны валидные номера анализов для удаления'
                }, status=status.HTTP_400_BAD_REQUEST)

            queryset = self.get_queryset().filter(id__in=parsed_ids)
            if not queryset.exists():
                return Response({
                    'success': False,
                    'error': 'Анализы по указанным номерам не найдены'
                }, status=status.HTTP_404_NOT_FOUND)

            existing_ids = list(queryset.values_list('id', flat=True))
            not_found = [i for i in parsed_ids if i not in existing_ids]

            # Режим предварительного просмотра (без удаления)
            if dry_run:
                return Response({
                    'success': True,
                    'requested_count': len(parsed_ids),
                    'would_delete_count': len(existing_ids),
                    'existing_ids': existing_ids,
                    'not_found': not_found or None
                }, status=status.HTTP_200_OK)

            deleted = 0
            errors = []
            deleted_ids = []

            for analysis in queryset:
                try:
                    try:
                        set_cancel_flag(analysis.id)
                    except Exception:
                        pass
                    analysis_id = analysis.id
                    analysis.delete()
                    deleted += 1
                    deleted_ids.append(analysis_id)
                except Exception as e:
                    errors.append(f"{analysis.id}: {str(e)}")

            return Response({
                'success': True,
                'deleted_count': deleted,
                'requested_count': len(parsed_ids),
                'deleted_ids': deleted_ids or None,
                'not_found': not_found or None,
                'errors': errors or None
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Ошибка при массовом удалении анализов: {e}")
            return Response({
                'success': False,
                'error': f'Ошибка при массовом удалении: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Удаление анализа: ставим флаг отмены и удаляем объект (файлы почистит сигнал)."""
        instance = self.get_object()
        try:
            # Ставим флаг отмены для фоновых задач
            set_cancel_flag(instance.id)
        except Exception:
            pass
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
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
            
            # Устанавливаем имя анализа строго по имени исходного фото (без расширения)
            try:
                original_filename = getattr(image_file, 'name', None) or ''
                base_name, _ = os.path.splitext(original_filename)
                analysis.name = (base_name or 'изображение').strip()
            except Exception:
                pass
            
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
            
            # Сбрасываем статус, ошибки и время запуска/завершения
            analysis.status = 'pending'
            analysis.error_message = ''
            analysis.start_time = timezone.now()
            analysis.end_time = None
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
        """Скачивание архива результатов отключено."""
        return Response({
            'error': 'Скачивание архива результатов отключено'
        }, status=status.HTTP_404_NOT_FOUND)
    
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
        
        # Приглушаем подробный вывод
        
        # Получаем список файлов
        result_files = analysis.get_result_files()
        
        # Приглушаем подробный вывод
        
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
        
        # Приглушаем подробный вывод
        
        if not filename:
            return Response({
                'error': 'Не указано имя файла'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file_path = os.path.join(analysis.results_directory, filename)
        # Приглушаем подробный вывод
        
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
                response = HttpResponse(file_content, content_type='image/png')
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                return response
        except Exception as e:
            # Приглушаем подробный вывод
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
    
    @action(detail=False, methods=['get'])
    def upload_config(self, request):
        """Получение конфигурации загрузки файлов"""
        try:
            upload_threads = PorosityAnalysisConfig.get_upload_threads()
            return Response({
                'upload_threads': upload_threads,
                'max_concurrent_uploads': upload_threads
            })
        except Exception as e:
            logger.error(f"Ошибка при получении конфигурации загрузки: {e}")
            return Response({
                'upload_threads': 8,  # Значение по умолчанию
                'max_concurrent_uploads': 8
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
                    
                    # Сбрасываем статус, время и результаты
                    analysis.status = 'pending'
                    analysis.error_message = ''
                    analysis.start_time = timezone.now()
                    analysis.end_time = None
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
    
    def _prepare_report_file_cached(self, analysis, report_type, file_cache):
        """Подготовка файла отчета с использованием кэша"""
        cache_key = f"{analysis.id}_{report_type}"
        
        # Проверяем кэш
        if cache_key in file_cache:
            cached_file = file_cache[cache_key]
            if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
                return cached_file, None
        
        try:
            # Ищем существующий файл отчета
            reports_dir = os.path.join(analysis.results_directory, 'reports')
            report_file = None
            
            if os.path.exists(reports_dir):
                for filename in os.listdir(reports_dir):
                    if filename.endswith(f'.{report_type}'):
                        report_file = os.path.join(reports_dir, filename)
                        break
            
            # Если файл не найден, генерируем новый
            if not report_file or not os.path.exists(report_file):
                from .report_generator import PorosityReportGenerator
                report_generator = PorosityReportGenerator(analysis)
                report_file = report_generator.generate_single_report(report_type)
            
            # Проверяем валидность файла
            if not report_file or not os.path.exists(report_file) or os.path.getsize(report_file) == 0:
                return None, f"Анализ {analysis.id}: не удалось подготовить отчет типа {report_type}"
            
            # Кэшируем файл
            file_cache[cache_key] = report_file
            return report_file, None
            
        except Exception as e:
            return None, f"Анализ {analysis.id}: {str(e)}"

    def _create_partial_archive(self, analyses_chunk, report_type, file_cache):
        """Создание частичного архива для группы анализов"""
        try:
            archive_buffer = io.BytesIO()
            successful_reports = 0
            failed_reports = []
            
            with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
                for analysis in analyses_chunk:
                    try:
                        report_file, error = self._prepare_report_file_cached(analysis, report_type, file_cache)
                        
                        if error:
                            failed_reports.append(error)
                            continue
                        
                        # Имя файла в архиве = имя исходного фото без расширения
                        base_photo_name = (analysis.name or '').strip() or f"analysis_{analysis.id}"
                        safe_name = re.sub(r'[^\w\s\-]', '', base_photo_name)[:100] or f"analysis_{analysis.id}"
                        archive_filename = f"{safe_name}.{report_type}"
                        
                        # Добавляем файл в архив
                        zip_file.write(report_file, archive_filename)
                        successful_reports += 1
                        
                    except Exception as e:
                        failed_reports.append(f"Анализ {analysis.id}: {str(e)}")
            
            archive_buffer.seek(0)
            return archive_buffer.getvalue(), successful_reports, failed_reports
            
        except Exception as e:
            return None, 0, [f"Ошибка создания частичного архива: {str(e)}"]

    def _merge_archives_fast(self, archive_parts, info_content=None):
        """Быстрое объединение частичных архивов"""
        try:
            final_buffer = io.BytesIO()
            
            with zipfile.ZipFile(final_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as final_zip:
                # Добавляем информационный файл, если есть
                if info_content:
                    final_zip.writestr('ИНФОРМАЦИЯ_О_ЗАПРОСЕ.txt', info_content.encode('utf-8'))
                
                # Объединяем все частичные архивы
                for i, archive_data in enumerate(archive_parts):
                    if archive_data is None:
                        continue
                        
                    with zipfile.ZipFile(io.BytesIO(archive_data), 'r') as partial_zip:
                        for file_info in partial_zip.infolist():
                            # Читаем данные файла
                            file_data = partial_zip.read(file_info.filename)
                            # Добавляем в финальный архив с префиксом для избежания конфликтов
                            final_filename = f"part_{i+1}/{file_info.filename}"
                            final_zip.writestr(final_filename, file_data)
            
            final_buffer.seek(0)
            return final_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка объединения архивов: {e}")
            return None

    @action(detail=False, methods=['post'])
    def download_multiple_reports(self, request):
        """Оптимизированное скачивание архива отчетов по нескольким анализам.
        
        Использует многопоточную подготовку файлов, кэширование и создание частичных архивов
        для максимальной скорости обработки больших объемов данных.
        
        Тело запроса может содержать:
        - analysis_ids | ids: массив чисел
        - input | ids_text: строка с номерами через запятую/тире/пробел
        - report_type: тип отчета ('docx' или 'pdf'), по умолчанию 'docx'
        """
        try:
            ids = request.data.get('analysis_ids') or request.data.get('ids')
            input_text = request.data.get('input') or request.data.get('ids_text') or ''
            report_type = request.data.get('report_type', 'docx')

            # Валидация типа отчета
            if report_type not in ['docx', 'pdf']:
                return Response({
                    'success': False,
                    'error': 'Неподдерживаемый тип отчета. Доступны: docx, pdf'
                }, status=status.HTTP_400_BAD_REQUEST)

            parsed_ids = []
            
            # Парсим ID из массива
            if isinstance(ids, list):
                parsed_ids.extend([int(x) for x in ids if str(x).isdigit()])
            
            # Парсим ID из строки (поддерживаем тире для диапазонов)
            if isinstance(input_text, str) and input_text.strip():
                # Сначала обрабатываем диапазоны (например, "1-5")
                parts = re.split(r'[,;\s]+', input_text.strip())
                for part in parts:
                    part = part.strip()
                    if '-' in part and not part.startswith('-'):
                        # Это диапазон
                        range_parts = part.split('-', 1)
                        if len(range_parts) == 2 and range_parts[0].isdigit() and range_parts[1].isdigit():
                            start = int(range_parts[0])
                            end = int(range_parts[1])
                            if start <= end:
                                parsed_ids.extend(range(start, end + 1))
                    elif part.isdigit():
                        parsed_ids.append(int(part))

            # Удаляем дубликаты и сортируем
            parsed_ids = list(sorted(set(parsed_ids)))

            if not parsed_ids:
                return Response({
                    'success': False,
                    'error': 'Не указаны валидные номера анализов'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Логируем большие запросы для мониторинга нагрузки
            if len(parsed_ids) > 100:
                logger.info(f"Большой запрос архива отчетов: {len(parsed_ids)} анализов, тип: {report_type}")

            # Получаем анализы
            queryset = self.get_queryset().filter(id__in=parsed_ids, status='completed')
            analyses = list(queryset)
            
            existing_ids = [analysis.id for analysis in analyses]
            not_found = [i for i in parsed_ids if i not in existing_ids]
            
            # Если нет ни одного завершенного анализа, создаем пустой архив с информацией
            if not analyses:
                archive_buffer = io.BytesIO()
                
                with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    info_content = f"""Информация о запросе архива отчетов

Запрошенные номера анализов: {', '.join(map(str, parsed_ids))}
Тип отчета: {report_type}
Дата запроса: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

РЕЗУЛЬТАТ:
Не найдено ни одного завершенного анализа по указанным номерам.

Возможные причины:
- Анализы с указанными номерами не существуют
- Анализы еще не завершены (находятся в процессе обработки)
- Анализы завершились с ошибкой

Проверьте статус анализов в интерфейсе системы.
"""
                    zip_file.writestr('ИНФОРМАЦИЯ.txt', info_content.encode('utf-8'))
                
                archive_buffer.seek(0)
                archive_content = archive_buffer.getvalue()
                
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                archive_filename = f"porosity_reports_empty_{report_type}_{timestamp}.zip"
                
                response = HttpResponse(archive_content, content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{archive_filename}"'
                response['Content-Length'] = len(archive_content)
                
                response['X-Reports-Count'] = '0'
                response['X-Failed-Count'] = '0'
                response['X-Not-Found'] = ','.join(map(str, not_found))
                
                logger.info(f"Создан пустой архив: не найдено анализов по номерам {parsed_ids}")
                return response

            # ОПТИМИЗИРОВАННАЯ ОБРАБОТКА
            from src.modules.porosity_analysis.config import PorosityAnalysisConfig
            
            # Инициализируем кэш файлов
            file_cache = {}
            cache_size_limit = PorosityAnalysisConfig.get_file_cache_size()
            
            # Определяем стратегию обработки в зависимости от количества анализов
            chunk_size = PorosityAnalysisConfig.get_archive_chunk_size()
            merge_threads = PorosityAnalysisConfig.get_archive_merge_threads()
            
            total_analyses = len(analyses)
            successful_reports = 0
            failed_reports = []
            
            # Для небольших объемов используем простую обработку
            if total_analyses <= chunk_size:
                logger.info(f"Обработка {total_analyses} анализов в одном потоке")
                
                archive_buffer = io.BytesIO()
                with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
                    # Добавляем информационный файл, если есть не найденные анализы
                    if not_found:
                        info_content = f"""Информация о запросе архива отчетов

Запрошенные номера анализов: {', '.join(map(str, parsed_ids))}
Найдено завершенных анализов: {len(existing_ids)} из {len(parsed_ids)}
Тип отчета: {report_type}
Дата запроса: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

НАЙДЕННЫЕ АНАЛИЗЫ:
{', '.join(map(str, existing_ids))}

НЕ НАЙДЕННЫЕ АНАЛИЗЫ:
{', '.join(map(str, not_found))}

Возможные причины отсутствия анализов:
- Анализы с указанными номерами не существуют
- Анализы еще не завершены (находятся в процессе обработки)
- Анализы завершились с ошибкой

Проверьте статус анализов в интерфейсе системы.
"""
                        zip_file.writestr('ИНФОРМАЦИЯ_О_ЗАПРОСЕ.txt', info_content.encode('utf-8'))
                    
                    # Обрабатываем анализы последовательно для небольших объемов
                    for analysis in analyses:
                        try:
                            report_file, error = self._prepare_report_file_cached(analysis, report_type, file_cache)
                            
                            if error:
                                failed_reports.append(error)
                                continue
                            
                            # Имя файла в архиве = имя исходного фото без расширения
                            base_photo_name = (analysis.name or '').strip() or f"analysis_{analysis.id}"
                            safe_name = re.sub(r'[^\w\s\-]', '', base_photo_name)[:100] or f"analysis_{analysis.id}"
                            archive_filename = f"{safe_name}.{report_type}"
                            
                            # Добавляем файл в архив
                            zip_file.write(report_file, archive_filename)
                            successful_reports += 1
                            
                        except Exception as e:
                            failed_reports.append(f"Анализ {analysis.id}: {str(e)}")
                
                archive_content = archive_buffer.getvalue()
                
            else:
                # Для больших объемов используем многопоточную обработку с частичными архивами
                logger.info(f"Обработка {total_analyses} анализов в {merge_threads} потоках с чанками по {chunk_size}")
                
                # Разбиваем анализы на чанки
                analysis_chunks = [analyses[i:i + chunk_size] for i in range(0, total_analyses, chunk_size)]
                
                # Создаем частичные архивы в нескольких потоках
                archive_parts = []
                with ThreadPoolExecutor(max_workers=merge_threads) as executor:
                    # Создаем задачи для каждого чанка
                    future_to_chunk = {
                        executor.submit(self._create_partial_archive, chunk, report_type, file_cache): i 
                        for i, chunk in enumerate(analysis_chunks)
                    }
                    
                    # Собираем результаты
                    for future in as_completed(future_to_chunk):
                        chunk_index = future_to_chunk[future]
                        try:
                            archive_data, chunk_successful, chunk_failed = future.result()
                            archive_parts.append(archive_data)
                            successful_reports += chunk_successful
                            failed_reports.extend(chunk_failed)
                            logger.info(f"Обработан чанк {chunk_index + 1}/{len(analysis_chunks)}: {chunk_successful} успешно, {len(chunk_failed)} ошибок")
                        except Exception as e:
                            logger.error(f"Ошибка обработки чанка {chunk_index + 1}: {e}")
                            archive_parts.append(None)
                            failed_reports.append(f"Чанк {chunk_index + 1}: {str(e)}")
                
                # Подготавливаем информационный контент
                info_content = None
                if not_found or failed_reports:
                    info_content = f"""Информация о запросе архива отчетов

Запрошенные номера анализов: {', '.join(map(str, parsed_ids))}
Найдено завершенных анализов: {len(existing_ids)} из {len(parsed_ids)}
Тип отчета: {report_type}
Дата запроса: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
Обработано чанков: {len(analysis_chunks)}

НАЙДЕННЫЕ АНАЛИЗЫ:
{', '.join(map(str, existing_ids))}

НЕ НАЙДЕННЫЕ АНАЛИЗЫ:
{', '.join(map(str, not_found))}

ОШИБКИ ПРИ ОБРАБОТКЕ:
{chr(10).join(failed_reports) if failed_reports else 'Ошибок не обнаружено'}

Возможные причины отсутствия анализов:
- Анализы с указанными номерами не существуют
- Анализы еще не завершены (находятся в процессе обработки)
- Анализы завершились с ошибкой

Проверьте статус анализов в интерфейсе системы.
"""
                
                # Объединяем частичные архивы
                archive_content = self._merge_archives_fast(archive_parts, info_content)
                
                if archive_content is None:
                    raise Exception("Не удалось объединить частичные архивы")

            # Если не удалось создать ни одного отчета, но анализы найдены
            if successful_reports == 0 and analyses:
                # Создаем архив только с информацией об ошибках
                archive_buffer = io.BytesIO()
                with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    error_info_content = f"""Информация об ошибках при создании отчетов

Запрошенные номера анализов: {', '.join(map(str, parsed_ids))}
Найдено завершенных анализов: {len(existing_ids)}
Тип отчета: {report_type}
Дата запроса: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

НАЙДЕННЫЕ АНАЛИЗЫ:
{', '.join(map(str, existing_ids))}

ОШИБКИ ПРИ СОЗДАНИИ ОТЧЕТОВ:
{chr(10).join(failed_reports)}

Рекомендации:
- Проверьте, что анализы действительно завершены успешно
- Убедитесь, что файлы результатов анализов не повреждены
- Обратитесь к администратору системы, если проблема повторяется
"""
                    zip_file.writestr('ОШИБКИ_СОЗДАНИЯ_ОТЧЕТОВ.txt', error_info_content.encode('utf-8'))
                
                archive_content = archive_buffer.getvalue()
                logger.warning(f"Создан архив только с информацией об ошибках для анализов {existing_ids}")

            # Формируем имя архива
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            archive_filename = f"porosity_reports_{report_type}_{timestamp}.zip"
            
            response = HttpResponse(archive_content, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{archive_filename}"'
            response['Content-Length'] = len(archive_content)
            
            # Добавляем информационные заголовки
            response['X-Reports-Count'] = str(successful_reports)
            response['X-Failed-Count'] = str(len(failed_reports))
            if not_found:
                response['X-Not-Found'] = ','.join(map(str, not_found))
            
            # Добавляем информацию о производительности
            response['X-Processing-Method'] = 'optimized' if total_analyses > chunk_size else 'simple'
            response['X-Cache-Size'] = str(len(file_cache))
            
            logger.info(f"Создан архив отчетов: {successful_reports} успешно, {len(failed_reports)} ошибок, метод: {'оптимизированный' if total_analyses > chunk_size else 'простой'}")
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при создании архива отчетов: {e}")
            return Response({
                'success': False,
                'error': f'Ошибка при создании архива: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
        
        # Приглушаем подробный вывод
        
        if analysis.status != 'completed':
            return Response({
                'error': 'Анализ еще не завершен'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Путь к директории отчетов
        reports_dir = os.path.join(analysis.results_directory, 'reports')
        # Приглушаем подробный вывод
        
        # Если отчеты еще не созданы, создаем их
        if not os.path.exists(reports_dir) or not os.listdir(reports_dir):
            # Приглушаем подробный вывод
            try:
                from .report_generator import PorosityReportGenerator
                report_generator = PorosityReportGenerator(analysis)
                reports = report_generator.generate_reports()
                # Приглушаем подробный вывод
                
                # Проверяем, что отчеты действительно созданы
                if not reports:
                    return Response({
                        'error': 'Не удалось сгенерировать отчеты'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                # Приглушаем подробный вывод
                return Response({
                    'error': f'Ошибка при генерации отчетов: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Ищем файл отчета
        report_files = []
        if os.path.exists(reports_dir):
            # Приглушаем подробный вывод
            for filename in os.listdir(reports_dir):
                # Приглушаем подробный вывод
                if filename.endswith(f'.{report_type}'):
                    report_files.append(filename)
                    # Приглушаем подробный вывод
        
        # Приглушаем подробный вывод
        
        if not report_files:
            # Попробуем сгенерировать отчеты еще раз
            # Приглушаем подробный вывод
            try:
                from .report_generator import PorosityReportGenerator
                report_generator = PorosityReportGenerator(analysis)
                reports = report_generator.generate_reports()
                # Приглушаем подробный вывод
                
                # Проверяем снова
                if os.path.exists(reports_dir):
                    for filename in os.listdir(reports_dir):
                        if filename.endswith(f'.{report_type}'):
                            report_files.append(filename)
                            # Приглушаем подробный вывод
            except Exception as e:
                pass
            
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
        
        # Приглушаем подробный вывод
        
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
            
            # Приглушаем подробный вывод
            
            # Отправляем файл
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
                # Имя скачиваемого файла = имя исходного фото без расширения
                base_photo_name = (analysis.name or '').strip() or f"analysis_{analysis.id}"
                safe_base = re.sub(r'[^\w\s\-]', '', base_photo_name)[:100] or f"analysis_{analysis.id}"
                download_filename = f"{safe_base}.{report_type}"

                response = HttpResponse(file_content, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{download_filename}"'
                response['Content-Length'] = len(file_content)
                return response
            
        except Exception as e:
            logger.error(f"Ошибка при чтении файла отчета: {str(e)}")
            return Response({
                'error': f'Ошибка при скачивании отчета: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)