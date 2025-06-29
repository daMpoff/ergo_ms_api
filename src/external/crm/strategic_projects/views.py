from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
import csv
import codecs
from .models import (
    DevelopmentProgram, ProgramTopic, StrategicProject,
    ProjectStage, StageExecutor, ProjectReport,
    StageResult, ProjectHistory
)
from .serializers import (
    DevelopmentProgramSerializer, ProgramTopicSerializer,
    StrategicProjectSerializer, StrategicProjectListSerializer,
    ProjectStageSerializer, StageExecutorSerializer,
    ProjectReportSerializer, StageResultSerializer,
    ProjectHistorySerializer, CreateProjectFromTopicSerializer,
    ImportProgramSerializer
)

User = get_user_model()


class DevelopmentProgramViewSet(viewsets.ModelViewSet):
    """ViewSet для управления программами развития"""
    queryset = DevelopmentProgram.objects.all()
    serializer_class = DevelopmentProgramSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'year']
    ordering_fields = ['year', 'created_at']
    
    @action(detail=False, methods=['post'])
    def import_program(self, request):
        """Импорт программы развития из CSV файла"""
        serializer = ImportProgramSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            year = serializer.validated_data['year']
            name = serializer.validated_data['name']
            
            try:
                # Создаем программу развития
                program = DevelopmentProgram.objects.create(
                    name=name,
                    year=year
                )
                
                # Читаем CSV файл
                csv_reader = csv.DictReader(codecs.iterdecode(file, 'utf-8'))
                topics_created = 0
                
                for row in csv_reader:
                    ProgramTopic.objects.create(
                        program=program,
                        direction_code=row.get('direction_code', ''),
                        topic_number=row.get('topic_number', ''),
                        name=row.get('name', ''),
                        description=row.get('description', ''),
                        planned_start_date=row.get('start_date'),
                        planned_end_date=row.get('end_date'),
                        expected_results=row.get('expected_results', '').split(';') if row.get('expected_results') else []
                    )
                    topics_created += 1
                
                return Response({
                    'message': f'Программа развития успешно импортирована. Создано тем: {topics_created}',
                    'program_id': program.id
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Ошибка при импорте: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProgramTopicViewSet(viewsets.ModelViewSet):
    """ViewSet для управления темами программы развития"""
    queryset = ProgramTopic.objects.all()
    serializer_class = ProgramTopicSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'direction_code', 'topic_number']
    ordering_fields = ['direction_code', 'topic_number']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по статусу
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Фильтр по программе
        program_id = self.request.query_params.get('program_id', None)
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def reserve_and_create_project(self, request, pk=None):
        """Бронирование темы и создание проекта"""
        topic = self.get_object()
        
        if topic.status != 'free':
            return Response({
                'error': 'Тема уже занята'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Создаем проект
            project = StrategicProject.objects.create(
                topic=topic,
                name=f"{topic.direction_code}-{topic.topic_number}: {topic.name}",
                leader=request.user,
                goal='',
                tasks='',
                planned_start_date=topic.planned_start_date,
                planned_end_date=topic.planned_end_date,
                planned_results=topic.expected_results
            )
            
            # Обновляем статус темы
            topic.status = 'reserved'
            topic.project = project
            topic.save()
            
            # Добавляем запись в историю
            ProjectHistory.objects.create(
                project=project,
                user=request.user,
                action='Создание проекта',
                description=f'Проект создан на основе темы {topic.name}'
            )
        
        serializer = StrategicProjectSerializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StrategicProjectViewSet(viewsets.ModelViewSet):
    """ViewSet для управления стратегическими проектами"""
    queryset = StrategicProject.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['created_at', 'status']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StrategicProjectListSerializer
        return StrategicProjectSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по статусу
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Фильтр "Мои проекты"
        my_projects = self.request.query_params.get('my_projects', None)
        if my_projects:
            queryset = queryset.filter(leader=self.request.user)
        
        # Фильтр для экспертной группы
        for_approval = self.request.query_params.get('for_approval', None)
        if for_approval:
            queryset = queryset.filter(status='on_approval')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        """Отправка проекта на утверждение"""
        project = self.get_object()
        
        if project.status != 'draft':
            return Response({
                'error': 'Проект должен быть в статусе "Черновик"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем заполненность полей
        if not all([project.goal, project.tasks, project.curator, project.customer]):
            return Response({
                'error': 'Не все обязательные поля заполнены'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем наличие этапов
        if not project.stages.exists():
            return Response({
                'error': 'Необходимо создать хотя бы один этап проекта'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        project.status = 'on_approval'
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Отправка на утверждение',
            description='Проект отправлен на рассмотрение экспертной группы'
        )
        
        return Response({
            'message': 'Проект успешно отправлен на утверждение'
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Утверждение проекта экспертной группой"""
        project = self.get_object()
        
        if project.status != 'on_approval':
            return Response({
                'error': 'Проект должен быть в статусе "На утверждении"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        project.status = 'approved'
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Утверждение проекта',
            description='Проект утвержден экспертной группой'
        )
        
        return Response({
            'message': 'Проект успешно утвержден'
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонение проекта экспертной группой"""
        project = self.get_object()
        
        if project.status != 'on_approval':
            return Response({
                'error': 'Проект должен быть в статусе "На утверждении"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        comment = request.data.get('comment', '')
        if not comment:
            return Response({
                'error': 'Необходимо указать причину отклонения'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        project.status = 'rejected'
        project.rejection_comment = comment
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Отклонение проекта',
            description=f'Проект отклонен. Причина: {comment}'
        )
        
        return Response({
            'message': 'Проект отклонен'
        })
    
    @action(detail=True, methods=['post'])
    def start_project(self, request, pk=None):
        """Запуск проекта в работу"""
        project = self.get_object()
        
        if project.status != 'approved':
            return Response({
                'error': 'Проект должен быть утвержден'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        project.status = 'in_progress'
        project.actual_start_date = timezone.now().date()
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Запуск проекта',
            description='Проект запущен в работу'
        )
        
        return Response({
            'message': 'Проект успешно запущен'
        })
    
    @action(detail=True, methods=['post'])
    def complete_project(self, request, pk=None):
        """Завершение проекта"""
        project = self.get_object()
        
        if project.status != 'in_progress':
            return Response({
                'error': 'Проект должен быть в работе'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что все этапы завершены
        incomplete_stages = project.stages.exclude(status='completed')
        if incomplete_stages.exists():
            return Response({
                'error': 'Не все этапы проекта завершены'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        project.status = 'completed'
        project.actual_end_date = timezone.now().date()
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Завершение проекта',
            description='Проект успешно завершен'
        )
        
        return Response({
            'message': 'Проект успешно завершен'
        })


class ProjectStageViewSet(viewsets.ModelViewSet):
    """ViewSet для управления этапами проекта"""
    queryset = ProjectStage.objects.all()
    serializer_class = ProjectStageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset
    
    @action(detail=True, methods=['post'])
    def start_stage(self, request, pk=None):
        """Начало работы над этапом"""
        stage = self.get_object()
        
        if stage.status != 'planned':
            return Response({
                'error': 'Этап уже начат или завершен'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        stage.status = 'in_progress'
        stage.actual_start_date = timezone.now().date()
        stage.save()
        
        return Response({
            'message': 'Этап успешно начат'
        })
    
    @action(detail=True, methods=['post'])
    def complete_stage(self, request, pk=None):
        """Завершение этапа"""
        stage = self.get_object()
        
        if stage.status != 'in_progress':
            return Response({
                'error': 'Этап должен быть в работе'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        stage.status = 'completed'
        stage.actual_end_date = timezone.now().date()
        stage.save()
        
        return Response({
            'message': 'Этап успешно завершен'
        })


class ProjectReportViewSet(viewsets.ModelViewSet):
    """ViewSet для управления отчетами"""
    queryset = ProjectReport.objects.all()
    serializer_class = ProjectReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset
    
    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        """Отправка отчета на согласование"""
        report = self.get_object()
        
        if report.approval_status != 'draft':
            return Response({
                'error': 'Отчет уже отправлен на согласование'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        report.approval_status = 'on_approval'
        report.save()
        
        return Response({
            'message': 'Отчет отправлен на согласование'
        })
    
    @action(detail=True, methods=['post'])
    def approve_report(self, request, pk=None):
        """Согласование отчета"""
        report = self.get_object()
        
        if report.approval_status != 'on_approval':
            return Response({
                'error': 'Отчет не находится на согласовании'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        report.approval_status = 'approved'
        report.save()
        
        return Response({
            'message': 'Отчет согласован'
        })


class StageResultViewSet(viewsets.ModelViewSet):
    """ViewSet для управления результатами этапов"""
    queryset = StageResult.objects.all()
    serializer_class = StageResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        stage_id = self.request.query_params.get('stage_id', None)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        return queryset 