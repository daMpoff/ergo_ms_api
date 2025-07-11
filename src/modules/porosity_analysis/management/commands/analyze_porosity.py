import os
import shutil
import uuid
import numpy as np
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.core.files import File

from src.modules.porosity_analysis.models import PorosityAnalysis
from src.modules.porosity_analysis.scripts.porosity_analyzer import PorosityAnalyzer


class Command(BaseCommand):
    help = 'Проводит анализ пористости изображения и сохраняет результаты в базу данных'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'image_path',
            type=str,
            help='Путь к изображению для анализа'
        )
        parser.add_argument(
            '--name',
            type=str,
            default=None,
            help='Название анализа (по умолчанию генерируется автоматически)'
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Описание анализа'
        )
        parser.add_argument(
            '--scale',
            type=float,
            default=100.0,
            help='Значение шкалы в микрометрах (по умолчанию 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезаписать существующие результаты'
        )
    
    def handle(self, *args, **options):
        image_path = options['image_path']
        name = options['name']
        description = options['description']
        scale_value = options['scale']
        force = options['force']
        
        # Проверка существования файла
        if not os.path.exists(image_path):
            raise CommandError(f'Файл не найден: {image_path}')
        
        # Проверка расширения файла
        if not self._is_valid_image(image_path):
            raise CommandError(f'Неподдерживаемый формат изображения: {image_path}')
        
        # Создание названия анализа
        if not name:
            name = self._generate_analysis_name(image_path)
        
        # Проверка существования анализа с таким именем
        if not force and PorosityAnalysis.objects.filter(name=name).exists():
            raise CommandError(f'Анализ с именем "{name}" уже существует. Используйте --force для перезаписи.')
        
        # Создание записи в БД
        analysis = self._create_analysis_record(name, description, image_path, scale_value)
        
        try:
            # Выполнение анализа
            self._perform_analysis(analysis, image_path, scale_value)
            
            self.stdout.write(
                self.style.SUCCESS(f'Анализ "{name}" успешно завершен!')
            )
            
        except Exception as e:
            # Обновление статуса при ошибке
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
            
            self.stdout.write(
                self.style.ERROR(f'Ошибка при выполнении анализа: {e}')
            )
            import traceback
            self.stdout.write(self.style.ERROR(f'Полная ошибка: {traceback.format_exc()}'))
            raise CommandError(f'Анализ завершился с ошибкой: {e}')
    
    def _is_valid_image(self, image_path):
        """Проверяет, является ли файл валидным изображением"""
        valid_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp']
        return any(image_path.lower().endswith(ext) for ext in valid_extensions)
    
    def _generate_analysis_name(self, image_path):
        """Генерирует название анализа на основе имени файла и времени"""
        filename = os.path.splitext(os.path.basename(image_path))[0]
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        return f"{filename}_{timestamp}"
    
    def _create_analysis_record(self, name, description, image_path, scale_value):
        """Создает запись анализа в базе данных"""
        # Генерируем UUID для результатов и исходного изображения
        results_uuid = str(uuid.uuid4())
        original_image_uuid = str(uuid.uuid4())
        
        analysis = PorosityAnalysis(
            name=name,
            description=description,
            scale_value=scale_value,
            status='processing',
            results_uuid=results_uuid,
            original_image_uuid=original_image_uuid
        )
        
        # Сохранение изображения в media с UUID
        original_image_path = os.path.join(
            settings.MEDIA_ROOT,
            'porosity_analysis',
            'initial_photo',
            f"{original_image_uuid}.png"
        )
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(original_image_path), exist_ok=True)
        
        # Копируем файл
        shutil.copy2(image_path, original_image_path)
        
        analysis.save()
        return analysis
    
    def _perform_analysis(self, analysis, image_path, scale_value):
        """Выполняет анализ пористости"""
        self.stdout.write(f'Начинаем анализ пористости для изображения: {image_path}')
        
        # Создание директории для результатов
        results_dir = self._create_results_directory(analysis)
        
        try:
            # Инициализация анализатора
            self.stdout.write('Инициализация анализатора...')
            analyzer = PorosityAnalyzer()
            
            # Выполнение анализа
            self.stdout.write('Выполнение анализа пористости...')
            results = analyzer.integrated_analysis(image_path, scale_value, results_dir)
            
            if results is None:
                raise Exception("Анализ не вернул результатов")
            
            self.stdout.write('Обновление результатов в базе данных...')
            # Обновление результатов в БД
            self._update_analysis_results(analysis, results)
            
            self.stdout.write('Проверка сохранения результатов...')
            # Проверка сохранения результатов
            self._copy_results_to_media(analysis, results_dir)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при анализе: {e}'))
            raise
    
    def _create_results_directory(self, analysis):
        """Создает директорию для результатов анализа"""
        results_dir = os.path.join(
            settings.MEDIA_ROOT,
            'porosity_analysis',
            'results',
            analysis.results_uuid
        )
        
        os.makedirs(results_dir, exist_ok=True)
        return results_dir
    
    def _update_analysis_results(self, analysis, results):
        """Обновляет результаты анализа в базе данных"""
        self.stdout.write('Обновление основных метрик...')
        
        # Основные метрики
        analysis.porosity_percentage = results.get('porosity_percentage', 0.0)
        analysis.number_of_pores = results.get('number_of_pores', 0)
        
        # Размеры пор
        pore_diameters = results.get('pore_diameters_microns', [])
        if pore_diameters is not None and len(pore_diameters) > 0:
            # Преобразуем numpy массив в список чисел
            if isinstance(pore_diameters, np.ndarray):
                pore_diameters = pore_diameters.tolist()
            
            # Фильтруем None значения и конвертируем в float
            diameters_list = []
            for d in pore_diameters:
                if d is not None and not (isinstance(d, float) and np.isnan(d)):
                    try:
                        diameters_list.append(float(d))
                    except (ValueError, TypeError):
                        continue
            
            if diameters_list:
                analysis.average_pore_size = sum(diameters_list) / len(diameters_list)
                analysis.max_pore_size = max(diameters_list)
                analysis.min_pore_size = min(diameters_list)
                self.stdout.write(f'Размеры пор: средний={analysis.average_pore_size:.2f}, '
                                f'макс={analysis.max_pore_size:.2f}, мин={analysis.min_pore_size:.2f} мкм')
        
        # Плотность пор
        pore_properties = results.get('pore_properties', [])
        if pore_properties is not None and len(pore_properties) > 0:
            total_area = results.get('total_area_microns', 1.0)
            # Проверяем, что total_area не является numpy массивом
            if isinstance(total_area, np.ndarray):
                total_area = float(total_area.item()) if total_area.size > 0 else 1.0
            elif hasattr(total_area, '__iter__') and not isinstance(total_area, (str, bytes)):
                total_area = float(total_area) if len(total_area) > 0 else 1.0
            else:
                total_area = float(total_area)
            
            analysis.pore_density = len(pore_properties) / total_area if total_area > 0 else 0.0
            self.stdout.write(f'Плотность пор: {analysis.pore_density:.4f} пор/мкм²')
        
        # Межпоровые расстояния
        interpore_distances = results.get('interpore_distances', [])
        if interpore_distances is not None and len(interpore_distances) > 0:
            # Преобразуем numpy массив в список чисел
            if isinstance(interpore_distances, np.ndarray):
                interpore_distances = interpore_distances.tolist()
            
            # Фильтруем None значения и конвертируем в float
            distances_list = []
            for d in interpore_distances:
                if d is not None and not (isinstance(d, float) and np.isnan(d)):
                    try:
                        distances_list.append(float(d))
                    except (ValueError, TypeError):
                        continue
            
            if distances_list:
                analysis.average_interpore_distance = sum(distances_list) / len(distances_list)
                self.stdout.write(f'Среднее межпоровое расстояние: {analysis.average_interpore_distance:.2f} мкм')
        
        # Масштаб
        pixels_per_micron = results.get('pixels_per_micron', 0.0)
        if isinstance(pixels_per_micron, np.ndarray):
            pixels_per_micron = float(pixels_per_micron.item())
        else:
            pixels_per_micron = float(pixels_per_micron)
        
        analysis.pixels_per_micron = pixels_per_micron
        self.stdout.write(f'Масштаб: {analysis.pixels_per_micron:.5f} пикселей/мкм')
        
        # Статус
        analysis.status = 'completed'
        
        analysis.save()
        self.stdout.write(self.style.SUCCESS('Результаты успешно сохранены в базе данных'))
    
    def _copy_results_to_media(self, analysis, results_dir):
        """Копирует результаты анализа в media директорию"""
        # Результаты уже находятся в правильной директории с UUID
        # Просто проверяем, что директория существует
        if not os.path.exists(results_dir):
            raise Exception(f"Директория результатов не найдена: {results_dir}")
        
        self.stdout.write(f'Результаты сохранены в: {results_dir}') 