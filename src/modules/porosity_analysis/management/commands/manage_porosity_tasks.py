from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from src.modules.porosity_analysis.models import PorosityAnalysis
from src.modules.porosity_analysis.tasks import run_porosity_analysis, cleanup_failed_analyses, validate_analysis_files


class Command(BaseCommand):
    help = 'Управление асинхронными задачами анализа пористости'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['run', 'restart', 'cleanup', 'validate', 'status', 'list'],
            help='Действие для выполнения'
        )
        parser.add_argument(
            '--analysis-id',
            type=int,
            help='ID анализа (для действий run и restart)'
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'processing', 'completed', 'failed'],
            help='Фильтр по статусу (для действия list)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Количество записей для отображения (по умолчанию 10)'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'run':
            self._run_analysis(options)
        elif action == 'restart':
            self._restart_analysis(options)
        elif action == 'cleanup':
            self._cleanup_failed_analyses()
        elif action == 'validate':
            self._validate_analysis_files()
        elif action == 'status':
            self._show_status()
        elif action == 'list':
            self._list_analyses(options)
    
    def _run_analysis(self, options):
        """Запуск анализа"""
        analysis_id = options.get('analysis_id')
        if not analysis_id:
            raise CommandError('Необходимо указать --analysis-id')
        
        try:
            analysis = PorosityAnalysis.objects.get(id=analysis_id)
            self.stdout.write(f'Запуск анализа ID {analysis_id}: {analysis.name}')
            
            # Запускаем асинхронную задачу
            task = run_porosity_analysis.delay(analysis_id)
            
            self.stdout.write(
                self.style.SUCCESS(f'Задача запущена с ID: {task.id}')
            )
            
        except PorosityAnalysis.DoesNotExist:
            raise CommandError(f'Анализ с ID {analysis_id} не найден')
    
    def _restart_analysis(self, options):
        """Перезапуск анализа"""
        analysis_id = options.get('analysis_id')
        if not analysis_id:
            raise CommandError('Необходимо указать --analysis-id')
        
        try:
            analysis = PorosityAnalysis.objects.get(id=analysis_id)
            self.stdout.write(f'Перезапуск анализа ID {analysis_id}: {analysis.name}')
            
            # Сбрасываем статус
            analysis.status = 'pending'
            analysis.error_message = ''
            analysis.save()
            
            # Запускаем асинхронную задачу
            task = run_porosity_analysis.delay(analysis_id)
            
            self.stdout.write(
                self.style.SUCCESS(f'Анализ перезапущен, задача ID: {task.id}')
            )
            
        except PorosityAnalysis.DoesNotExist:
            raise CommandError(f'Анализ с ID {analysis_id} не найден')
    
    def _cleanup_failed_analyses(self):
        """Очистка неудачных анализов"""
        self.stdout.write('Запуск очистки неудачных анализов...')
        
        # Выполняем задачу синхронно
        cleanup_failed_analyses.delay()
        
        self.stdout.write(
            self.style.SUCCESS('Задача очистки запущена')
        )
    
    def _validate_analysis_files(self):
        """Проверка целостности файлов"""
        self.stdout.write('Запуск проверки целостности файлов...')
        
        # Выполняем задачу синхронно
        validate_analysis_files.delay()
        
        self.stdout.write(
            self.style.SUCCESS('Задача проверки запущена')
        )
    
    def _show_status(self):
        """Показать статистику анализов"""
        total = PorosityAnalysis.objects.count()
        pending = PorosityAnalysis.objects.filter(status='pending').count()
        processing = PorosityAnalysis.objects.filter(status='processing').count()
        completed = PorosityAnalysis.objects.filter(status='completed').count()
        failed = PorosityAnalysis.objects.filter(status='failed').count()
        
        self.stdout.write('Статистика анализов пористости:')
        self.stdout.write(f'  Всего: {total}')
        self.stdout.write(f'  Ожидают: {pending}')
        self.stdout.write(f'  Обрабатываются: {processing}')
        self.stdout.write(f'  Завершены: {completed}')
        self.stdout.write(f'  Ошибки: {failed}')
        
        if total > 0:
            success_rate = (completed / total) * 100
            self.stdout.write(f'  Процент успеха: {success_rate:.1f}%')
    
    def _list_analyses(self, options):
        """Список анализов"""
        status_filter = options.get('status')
        limit = options.get('limit')
        
        queryset = PorosityAnalysis.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        analyses = queryset.order_by('-created_at')[:limit]
        
        if not analyses:
            self.stdout.write('Анализы не найдены')
            return
        
        self.stdout.write(f'Список анализов (показано {len(analyses)} из {queryset.count()}):')
        self.stdout.write('')
        
        for analysis in analyses:
            status_color = {
                'pending': 'yellow',
                'processing': 'blue',
                'completed': 'green',
                'failed': 'red'
            }.get(analysis.status, 'white')
            
            self.stdout.write(
                f'ID {analysis.id}: {analysis.name} '
                f'({self.style.SUCCESS(analysis.status) if analysis.status == "completed" else self.style.WARNING(analysis.status) if analysis.status == "processing" else self.style.ERROR(analysis.status)})'
            )
            self.stdout.write(f'  Создан: {analysis.created_at.strftime("%Y-%m-%d %H:%M")}')
            
            if analysis.status == 'completed':
                self.stdout.write(f'  Пористость: {analysis.porosity_percentage:.2f}%')
                self.stdout.write(f'  Количество пор: {analysis.number_of_pores}')
            
            if analysis.status == 'failed' and analysis.error_message:
                self.stdout.write(f'  Ошибка: {analysis.error_message}')
            
            self.stdout.write('') 