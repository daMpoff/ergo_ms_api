from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import HttpResponse
import csv
import codecs
import json
from datetime import datetime, timedelta
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import xlsxwriter
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from src.core.utils.mixins import SwaggerSafeMixin
from .models import (
    DevelopmentProgram, ProgramTopic, StrategicProject,
    ProjectStage, StageExecutor, ProjectReport,
    StageResult, ProjectHistory, UserProjectRole, EmployeeWorkload,
    ProjectNotification
)
from .serializers import (
    DevelopmentProgramSerializer, ProgramTopicSerializer,
    StrategicProjectSerializer, StrategicProjectListSerializer,
    ProjectStageSerializer, StageExecutorSerializer,
    ProjectReportSerializer, StageResultSerializer,
    ProjectHistorySerializer, CreateProjectFromTopicSerializer,
    ImportProgramSerializer, UserProjectRoleSerializer,
    EmployeeWorkloadSerializer, ProjectNotificationSerializer
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
        
        old_status = project.status
        project.status = 'on_approval'
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Отправка на утверждение',
            description='Проект отправлен на рассмотрение экспертной группы'
        )
        
        # Отправляем уведомления
        ProjectNotification.notify_status_change(project, old_status, project.status)
        
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
        
        old_status = project.status
        project.status = 'approved'
        project.save()
        
        # Добавляем запись в историю
        ProjectHistory.objects.create(
            project=project,
            user=request.user,
            action='Утверждение проекта',
            description='Проект утвержден экспертной группой'
        )
        
        # Отправляем уведомления
        ProjectNotification.notify_status_change(project, old_status, project.status)
        
        # Отправляем специальное уведомление руководителю проекта
        ProjectNotification.create_notification(
            project=project,
            recipient=project.leader,
            notification_type='project_approved',
            title=f'Ваш проект "{project.name}" утвержден!',
            message=f'Экспертная группа утвердила ваш проект. Теперь вы можете запустить его в работу.'
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
        
        old_status = project.status
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
        
        # Отправляем уведомления
        ProjectNotification.notify_status_change(project, old_status, project.status)
        
        # Отправляем специальное уведомление руководителю проекта
        ProjectNotification.create_notification(
            project=project,
            recipient=project.leader,
            notification_type='project_rejected',
            title=f'Ваш проект "{project.name}" отклонен',
            message=f'Экспертная группа отклонила ваш проект.\n\nПричина: {comment}'
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
        
        old_status = project.status
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
        
        # Отправляем уведомления
        ProjectNotification.notify_status_change(project, old_status, project.status)
        
        # Отправляем специальное уведомление участникам проекта
        recipients = [project.leader]
        if project.curator:
            recipients.append(project.curator)
        if project.customer:
            recipients.append(project.customer)
            
        for recipient in set(recipients):
            ProjectNotification.create_notification(
                project=project,
                recipient=recipient,
                notification_type='project_started',
                title=f'Проект "{project.name}" запущен в работу',
                message=f'Проект официально запущен. Дата начала: {project.actual_start_date}'
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
        
        old_status = project.status
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
        
        # Отправляем уведомления
        ProjectNotification.notify_status_change(project, old_status, project.status)
        
        # Отправляем специальное уведомление участникам проекта
        recipients = [project.leader]
        if project.curator:
            recipients.append(project.curator)
        if project.customer:
            recipients.append(project.customer)
            
        for recipient in set(recipients):
            ProjectNotification.create_notification(
                project=project,
                recipient=recipient,
                notification_type='project_completed',
                title=f'Проект "{project.name}" успешно завершен!',
                message=f'Поздравляем! Проект завершен. Дата завершения: {project.actual_end_date}'
            )
        
        return Response({
            'message': 'Проект успешно завершен'
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получение статистики по проектам"""
        queryset = self.get_queryset()
        
        # Базовая статистика
        total_projects = queryset.count()
        status_stats = queryset.values('status').annotate(count=Count('id'))
        
        # Статистика по программам развития
        program_stats = queryset.values('topic__program__name', 'topic__program__year').annotate(
            count=Count('id')
        )
        
        # Статистика по руководителям
        leader_stats = queryset.values('leader__id', 'leader__first_name', 'leader__last_name').annotate(
            projects_count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        )
        
        # Статистика по месяцам (последние 6 месяцев)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = []
        
        for i in range(6):
            month_start = six_months_ago + timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            
            created_count = queryset.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            
            completed_count = queryset.filter(
                status='completed',
                actual_end_date__gte=month_start.date(),
                actual_end_date__lt=month_end.date()
            ).count()
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'created': created_count,
                'completed': completed_count
            })
        
        return Response({
            'total_projects': total_projects,
            'status_statistics': status_stats,
            'program_statistics': program_stats,
            'leader_statistics': leader_stats,
            'monthly_statistics': monthly_stats
        })
    
    @action(detail=False, methods=['get'])
    def charts(self, request):
        """Получение данных для графиков"""
        chart_type = request.query_params.get('type', 'status')
        queryset = self.get_queryset()
        
        if chart_type == 'status':
            # Данные для круговой диаграммы статусов
            data = queryset.values('status').annotate(count=Count('id'))
            return Response({
                'type': 'pie',
                'data': data
            })
        
        elif chart_type == 'timeline':
            # Данные для временной шкалы
            projects = queryset.order_by('planned_start_date')[:20]
            data = []
            for project in projects:
                data.append({
                    'id': project.id,
                    'name': project.name,
                    'start': project.planned_start_date,
                    'end': project.planned_end_date,
                    'status': project.status
                })
            return Response({
                'type': 'timeline',
                'data': data
            })
        
        elif chart_type == 'workload':
            # Данные по загруженности
            workload_data = EmployeeWorkload.objects.filter(
                project__in=queryset
            ).values('user__first_name', 'user__last_name').annotate(
                total_workload=Sum('workload_percentage')
            )
            return Response({
                'type': 'bar',
                'data': workload_data
            })
        
        return Response({'error': 'Неизвестный тип графика'}, status=400)
    
    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """Генерация отчета в различных форматах"""
        report_type = request.data.get('type', 'summary')
        format_type = request.data.get('format', 'pdf')
        filters = request.data.get('filters', {})
        
        # Применяем фильтры
        queryset = self.get_queryset()
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        if filters.get('program'):
            queryset = queryset.filter(topic__program_id=filters['program'])
        if filters.get('start_date'):
            queryset = queryset.filter(created_at__gte=filters['start_date'])
        if filters.get('end_date'):
            queryset = queryset.filter(created_at__lte=filters['end_date'])
        
        # Генерируем отчет в зависимости от формата
        if format_type == 'pdf':
            return self._generate_pdf_report(queryset, report_type)
        elif format_type == 'excel':
            return self._generate_excel_report(queryset, report_type)
        elif format_type == 'word':
            return self._generate_word_report(queryset, report_type)
        elif format_type == 'csv':
            return self._generate_csv_report(queryset, report_type)
        
        return Response({'error': 'Неподдерживаемый формат'}, status=400)
    
    def _generate_pdf_report(self, queryset, report_type):
        """Генерация PDF отчета"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Стили
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            alignment=1  # По центру
        )
        
        # Заголовок
        elements.append(Paragraph("Отчет по стратегическим проектам", title_style))
        elements.append(Spacer(1, 0.5 * inch))
        
        # Информация об отчете
        info_text = f"Дата формирования: {timezone.now().strftime('%d.%m.%Y %H:%M')}<br/>"
        info_text += f"Количество проектов: {queryset.count()}<br/>"
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Таблица с проектами
        data = [['Код', 'Название', 'Статус', 'Руководитель', 'Даты']]
        
        for project in queryset[:50]:  # Ограничиваем количество
            data.append([
                project.code,
                Paragraph(project.name[:50] + '...' if len(project.name) > 50 else project.name, styles['Normal']),
                self._get_status_display(project.status),
                project.leader.get_full_name(),
                f"{project.planned_start_date.strftime('%d.%m.%Y')} - {project.planned_end_date.strftime('%d.%m.%Y')}"
            ])
        
        table = Table(data, colWidths=[1.5*inch, 2.5*inch, 1.2*inch, 1.5*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Генерируем PDF
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="strategic_projects_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        return response
    
    def _generate_excel_report(self, queryset, report_type):
        """Генерация Excel отчета"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Стратегические проекты')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#667eea',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Заголовки
        headers = ['Код', 'Название', 'Статус', 'Руководитель', 'Куратор', 
                   'Заказчик', 'Дата начала', 'Дата окончания', 'Цель', 'Задачи']
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Данные
        row = 1
        for project in queryset:
            worksheet.write(row, 0, project.code)
            worksheet.write(row, 1, project.name)
            worksheet.write(row, 2, self._get_status_display(project.status))
            worksheet.write(row, 3, project.leader.get_full_name())
            worksheet.write(row, 4, project.curator.get_full_name() if project.curator else '')
            worksheet.write(row, 5, project.customer.get_full_name() if project.customer else '')
            worksheet.write(row, 6, project.planned_start_date.strftime('%d.%m.%Y'))
            worksheet.write(row, 7, project.planned_end_date.strftime('%d.%m.%Y'))
            worksheet.write(row, 8, project.goal)
            worksheet.write(row, 9, project.tasks)
            row += 1
        
        # Автоподбор ширины колонок
        for col in range(len(headers)):
            worksheet.set_column(col, col, 15)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="strategic_projects_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
    
    def _generate_word_report(self, queryset, report_type):
        """Генерация Word отчета"""
        document = Document()
        
        # Заголовок
        title = document.add_heading('Отчет по стратегическим проектам', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Информация об отчете
        document.add_paragraph(f'Дата формирования: {timezone.now().strftime("%d.%m.%Y %H:%M")}')
        document.add_paragraph(f'Количество проектов: {queryset.count()}')
        
        # Таблица с проектами
        table = document.add_table(rows=1, cols=5)
        table.style = 'Light Grid Accent 1'
        
        # Заголовки таблицы
        headers = ['Код', 'Название', 'Статус', 'Руководитель', 'Сроки']
        for i, header in enumerate(headers):
            table.rows[0].cells[i].text = header
        
        # Данные
        for project in queryset[:50]:
            row = table.add_row()
            row.cells[0].text = project.code
            row.cells[1].text = project.name
            row.cells[2].text = self._get_status_display(project.status)
            row.cells[3].text = project.leader.get_full_name()
            row.cells[4].text = f"{project.planned_start_date.strftime('%d.%m.%Y')} - {project.planned_end_date.strftime('%d.%m.%Y')}"
        
        # Сохраняем в буфер
        output = io.BytesIO()
        document.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="strategic_projects_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.docx"'
        
        return response
    
    def _generate_csv_report(self, queryset, report_type):
        """Генерация CSV отчета"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="strategic_projects_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Код', 'Название', 'Статус', 'Руководитель', 'Куратор', 
                        'Заказчик', 'Дата начала', 'Дата окончания', 'Цель', 'Задачи'])
        
        for project in queryset:
            writer.writerow([
                project.code,
                project.name,
                self._get_status_display(project.status),
                project.leader.get_full_name(),
                project.curator.get_full_name() if project.curator else '',
                project.customer.get_full_name() if project.customer else '',
                project.planned_start_date.strftime('%d.%m.%Y'),
                project.planned_end_date.strftime('%d.%m.%Y'),
                project.goal,
                project.tasks
            ])
        
        return response
    
    def _get_status_display(self, status):
        """Получение отображаемого названия статуса"""
        status_map = {
            'draft': 'Черновик',
            'on_approval': 'На утверждении',
            'rejected': 'Отклонен',
            'approved': 'Утвержден',
            'in_progress': 'В работе',
            'completed': 'Завершен',
            'archived': 'Архив'
        }
        return status_map.get(status, status)
    
    @action(detail=False, methods=['get'])
    def recent_reports(self, request):
        """Получение списка последних сформированных отчетов (заглушка)"""
        # В реальном приложении здесь должна быть модель для хранения истории отчетов
        mock_reports = []
        for i in range(5):
            mock_reports.append({
                'id': i + 1,
                'type': ['summary', 'detailed', 'financial', 'progress', 'workload'][i % 5],
                'period_label': ['Текущий месяц', 'Прошлый квартал', 'Год 2023'][i % 3],
                'format': ['pdf', 'excel', 'word', 'csv'][i % 4],
                'created_at': (timezone.now() - timedelta(days=i)).isoformat(),
                'created_by_name': ['Иванов И.И.', 'Петров П.П.', 'Сидоров С.С.'][i % 3],
                'download_url': f'/api/crm/strategic-projects/reports/{i+1}/download/',
                'view_url': f'/api/crm/strategic-projects/reports/{i+1}/view/'
            })
        
        return Response(mock_reports)


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


class UserProjectRoleViewSet(viewsets.ModelViewSet):
    """ViewSet для управления ролями пользователей в стратегических проектах"""
    queryset = UserProjectRole.objects.all()
    serializer_class = UserProjectRoleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтр по пользователю
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        # Фильтр по роли
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_role(self, request):
        """Получение роли текущего пользователя"""
        try:
            role = UserProjectRole.objects.get(user=request.user)
            serializer = self.get_serializer(role)
            return Response(serializer.data)
        except UserProjectRole.DoesNotExist:
            return Response({
                'role': None,
                'message': 'Роль не назначена'
            })
    
    @action(detail=False, methods=['post'])
    def assign_role(self, request):
        """Назначение роли пользователю (только для администраторов)"""
        # Проверяем, что текущий пользователь - администратор
        try:
            current_role = UserProjectRole.objects.get(user=request.user)
            if current_role.role != 'admin':
                return Response({
                    'error': 'Только администратор может назначать роли'
                }, status=status.HTTP_403_FORBIDDEN)
        except UserProjectRole.DoesNotExist:
            return Response({
                'error': 'У вас нет прав для назначения ролей'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        role = request.data.get('role')
        
        if not user_id or not role:
            return Response({
                'error': 'Необходимо указать user_id и role'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            user_role, created = UserProjectRole.objects.update_or_create(
                user=user,
                defaults={
                    'role': role,
                    'created_by': request.user
                }
            )
            
            action = 'назначена' if created else 'обновлена'
            return Response({
                'message': f'Роль {action} успешно',
                'data': UserProjectRoleSerializer(user_role).data
            })
        except User.DoesNotExist:
            return Response({
                'error': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)


class EmployeeWorkloadViewSet(viewsets.ModelViewSet):
    """ViewSet для управления загруженностью сотрудников"""
    queryset = EmployeeWorkload.objects.all()
    serializer_class = EmployeeWorkloadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтр по пользователю
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        # Фильтр по проекту
        project_id = self.request.query_params.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def workload_summary(self, request):
        """Получение сводки по загруженности всех сотрудников"""
        # Получаем текущую дату
        today = timezone.now().date()
        
        # Агрегируем загруженность по пользователям
        workload_data = EmployeeWorkload.objects.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today),
            start_date__lte=today
        ).values('user__id', 'user__first_name', 'user__last_name').annotate(
            total_workload=Sum('workload_percentage')
        )
        
        # Формируем ответ
        summary = []
        for data in workload_data:
            summary.append({
                'user_id': data['user__id'],
                'user_name': f"{data['user__first_name']} {data['user__last_name']}",
                'total_workload': data['total_workload'] or 0,
                'status': self._get_workload_status(data['total_workload'] or 0)
            })
        
        return Response({
            'count': len(summary),
            'data': summary
        })
    
    def _get_workload_status(self, workload):
        """Определение статуса загруженности"""
        if workload < 70:
            return 'underloaded'
        elif workload <= 100:
            return 'optimal'
        else:
            return 'overloaded'
    
    @action(detail=False, methods=['get'])
    def my_workload(self, request):
        """Получение загруженности текущего пользователя"""
        today = timezone.now().date()
        workload = EmployeeWorkload.objects.filter(
            user=request.user
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        )
        
        total_workload = sum(w.workload_percentage for w in workload)
        
        serializer = self.get_serializer(workload, many=True)
        return Response({
            'total_workload': total_workload,
            'status': self._get_workload_status(total_workload),
            'projects': serializer.data
        })


class ProjectNotificationViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для управления уведомлениями по стратегическим проектам"""
    serializer_class = ProjectNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return ProjectNotification.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return ProjectNotification.objects.none()
            
        # Пользователь видит только свои уведомления
        queryset = ProjectNotification.objects.filter(recipient=user)
        
        # Фильтр по статусу прочтения
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Фильтр по типу уведомления
        notification_type = self.request.query_params.get('notification_type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Фильтр по проекту
        project_id = self.request.query_params.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Отметить уведомление как прочитанное"""
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'message': 'Уведомление отмечено как прочитанное'
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Отметить все уведомления как прочитанные"""
        notifications = self.get_queryset().filter(is_read=False)
        count = notifications.count()
        
        for notification in notifications:
            notification.mark_as_read()
        
        return Response({
            'message': f'Отмечено как прочитанное: {count} уведомлений'
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Получить количество непрочитанных уведомлений"""
        count = self.get_queryset().filter(is_read=False).count()
        
        return Response({
            'unread_count': count
        })
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Получить последние уведомления"""
        limit = int(request.query_params.get('limit', 10))
        notifications = self.get_queryset()[:limit]
        serializer = self.get_serializer(notifications, many=True)
        
        return Response(serializer.data) 