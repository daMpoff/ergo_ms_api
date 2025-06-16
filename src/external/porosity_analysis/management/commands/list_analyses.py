"""
Команда для просмотра списка анализов пористости
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from src.external.porosity_analysis.models import PorosityAnalysis


class Command(BaseCommand):
    help = 'Просмотр списка анализов пористости'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Показать анализы только для указанного пользователя'
        )
        
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'processing', 'completed', 'failed'],
            help='Фильтр по статусу анализа'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Показать анализы за последние N дней (по умолчанию: 30)'
        )
        
        parser.add_argument(
            '--detail',
            action='store_true',
            help='Показать детальную информацию'
        )

    def handle(self, *args, **options):
        # Фильтрация анализов
        queryset = PorosityAnalysis.objects.all()
        
        # Фильтр по пользователю
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
                queryset = queryset.filter(user=user)
                self.stdout.write(f"Анализы пользователя: {user.username}")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Пользователь с ID {options['user_id']} не найден")
                )
                return
        
        # Фильтр по статусу
        if options['status']:
            queryset = queryset.filter(status=options['status'])
            self.stdout.write(f"Статус: {options['status']}")
        
        # Фильтр по дате
        days = options['days']
        if days > 0:
            date_from = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(created_at__gte=date_from)
            self.stdout.write(f"За последние {days} дней")
        
        # Сортировка по дате создания
        queryset = queryset.order_by('-created_at')
        
        if not queryset.exists():
            self.stdout.write(self.style.WARNING("Анализы не найдены"))
            return
        
        self.stdout.write(f"\nВсего найдено анализов: {queryset.count()}")
        self.stdout.write("=" * 80)
        
        for analysis in queryset:
            self._print_analysis(analysis, options['detail'])
            self.stdout.write("-" * 80)

    def _print_analysis(self, analysis: PorosityAnalysis, show_detail: bool):
        """Вывод информации об анализе"""
        # Основная информация
        status_color = {
            'pending': self.style.WARNING,
            'processing': self.style.HTTP_INFO,
            'completed': self.style.SUCCESS,
            'failed': self.style.ERROR
        }
        
        status_display = status_color.get(analysis.status, self.style.SUCCESS)(
            analysis.get_status_display()
        )
        
        self.stdout.write(f"ID: {analysis.id}")
        self.stdout.write(f"Название: {analysis.name}")
        self.stdout.write(f"Пользователь: {analysis.user.username}")
        self.stdout.write(f"Статус: {status_display}")
        self.stdout.write(f"Создан: {analysis.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Обновлен: {analysis.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Шкала: {analysis.scale_value} мкм")
        
        # Количество изображений
        images_count = analysis.images.count()
        self.stdout.write(f"Изображений: {images_count}")
        
        # Результаты если анализ завершен
        if analysis.status == 'completed' and analysis.porosity_percentage is not None:
            self.stdout.write(f"Пористость: {analysis.porosity_percentage:.2f}%")
            self.stdout.write(f"Количество пор: {analysis.number_of_pores}")
            if analysis.average_pore_diameter:
                self.stdout.write(f"Средний диаметр пор: {analysis.average_pore_diameter:.2f} мкм")
            if analysis.total_pore_area:
                self.stdout.write(f"Общая площадь пор: {analysis.total_pore_area:.2f} мкм²")
        
        # Ошибка если есть
        if analysis.status == 'failed' and analysis.error_message:
            self.stdout.write(
                self.style.ERROR(f"Ошибка: {analysis.error_message}")
            )
        
        # Путь к результатам
        if analysis.results_directory:
            self.stdout.write(f"Папка результатов: {analysis.results_directory}")
        
        # Детальная информация
        if show_detail:
            self._print_detailed_info(analysis)

    def _print_detailed_info(self, analysis: PorosityAnalysis):
        """Вывод детальной информации"""
        self.stdout.write("\nДетальная информация:")
        
        # Информация об изображениях
        if analysis.images.exists():
            self.stdout.write("  Изображения:")
            for i, image in enumerate(analysis.images.all(), 1):
                self.stdout.write(f"    {i}. {image.filename}")
                if image.image_porosity_percentage is not None:
                    self.stdout.write(f"       Пористость: {image.image_porosity_percentage:.2f}%")
                if image.image_number_of_pores is not None:
                    self.stdout.write(f"       Пор: {image.image_number_of_pores}")
                if image.image_average_pore_diameter is not None:
                    self.stdout.write(f"       Ср. диаметр: {image.image_average_pore_diameter:.2f} мкм")
        
        # Информация о визуализациях
        visualizations = analysis.visualizations.all()
        if visualizations.exists():
            self.stdout.write("  Визуализации:")
            for viz in visualizations:
                viz_name = dict(viz.VISUALIZATION_TYPES).get(viz.visualization_type, viz.visualization_type)
                self.stdout.write(f"    - {viz_name}")
        
        # Детальные результаты
        if hasattr(analysis, 'detailed_results') and analysis.detailed_results:
            details = analysis.detailed_results
            self.stdout.write("  Детальные результаты:")
            
            if details.pore_size_distribution:
                self.stdout.write("    - Распределение размеров пор: есть")
            if details.interpore_distances:
                self.stdout.write("    - Межпоровые расстояния: есть")
            if details.pore_orientation:
                self.stdout.write("    - Ориентация пор: есть")
            if details.pore_shapes:
                self.stdout.write("    - Формы пор: есть") 