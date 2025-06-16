"""
Django команда для анализа пористости фотографий с микроскопа
"""
import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.base import ContentFile

from src.external.porosity_analysis.models import (
    PorosityAnalysis, 
    PorosityImage, 
    PorosityResults, 
    PorosityVisualization
)
from src.external.porosity_analysis.methods import PorosityAnalyzer


class Command(BaseCommand):
    help = 'Анализ пористости фотографий с микроскопа'

    def add_arguments(self, parser):
        parser.add_argument(
            'image_path',
            type=str,
            help='Путь к изображению или папке с изображениями'
        )
        
        parser.add_argument(
            '--output-dir',
            type=str,
            default='porosity_results',
            help='Директория для сохранения результатов (по умолчанию: porosity_results)'
        )
        
        parser.add_argument(
            '--scale-value',
            type=float,
            default=100.0,
            help='Значение шкалы в микрометрах (по умолчанию: 100.0)'
        )
        
        parser.add_argument(
            '--name',
            type=str,
            help='Название анализа (по умолчанию: генерируется автоматически)'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID пользователя (по умолчанию: создается системный пользователь)'
        )
        
        parser.add_argument(
            '--save-to-db',
            action='store_true',
            help='Сохранить результаты в базу данных'
        )
        
        parser.add_argument(
            '--file-formats',
            nargs='+',
            default=['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
            help='Поддерживаемые форматы файлов'
        )

    def handle(self, *args, **options):
        try:
            # Проверка входных параметров
            image_path = Path(options['image_path'])
            output_dir = Path(options['output_dir'])
            scale_value = options['scale_value']
            analysis_name = options['name']
            user_id = options['user_id']
            save_to_db = options['save_to_db']
            file_formats = options['file_formats']
            
            # Валидация scale_value
            if scale_value <= 0 or scale_value > 10000:
                raise CommandError('scale_value должно быть между 0.1 и 10000.0')
            
            # Проверка существования входного файла/директории
            if not image_path.exists():
                raise CommandError(f'Путь не существует: {image_path}')
            
            # Получение списка изображений
            image_files = self._get_image_files(image_path, file_formats)
            if not image_files:
                raise CommandError(f'Не найдено изображений в {image_path}')
            
            self.stdout.write(
                self.style.SUCCESS(f'Найдено {len(image_files)} изображений для анализа')
            )
            
            # Создание директории для результатов
            analysis_id = str(uuid.uuid4())
            results_dir = output_dir / analysis_id
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Генерация названия анализа
            if not analysis_name:
                analysis_name = f'Анализ пористости {analysis_id[:8]}'
            
            # Создание записи в БД если требуется
            analysis = None
            if save_to_db:
                user = self._get_or_create_user(user_id)
                analysis = PorosityAnalysis.objects.create(
                    user=user,
                    name=analysis_name,
                    scale_value=scale_value,
                    status='processing',
                    results_directory=str(results_dir)
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Создан анализ в БД с ID: {analysis.id}')
                )
            
            # Инициализация анализатора
            analyzer = PorosityAnalyzer()
            
            # Обработка изображений
            all_results = []
            for i, image_file in enumerate(image_files):
                self.stdout.write(f'Обработка {i+1}/{len(image_files)}: {image_file.name}')
                
                try:
                    # Создание папки для результатов изображения
                    image_results_dir = results_dir / f"image_{i}_{image_file.stem}"
                    image_results_dir.mkdir(exist_ok=True)
                    
                    # Анализ изображения
                    results = analyzer.analyze_image(
                        str(image_file),
                        scale_value,
                        str(image_results_dir)
                    )
                    
                    if results:
                        all_results.append(results)
                        
                        # Сохранение изображения в БД если требуется
                        if save_to_db and analysis:
                            self._save_image_to_db(analysis, image_file, results)
                        
                        # Вывод основных результатов
                        self._print_image_results(image_file.name, results)
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Не удалось обработать {image_file.name}')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Ошибка при обработке {image_file.name}: {e}')
                    )
            
            if not all_results:
                raise CommandError('Не удалось обработать ни одного изображения')
            
            # Сводные результаты
            summary = self._calculate_summary(all_results)
            
            # Обновление анализа в БД
            if save_to_db and analysis:
                self._update_analysis_results(analysis, summary, all_results, results_dir)
            
            # Сохранение сводного отчета
            self._save_summary_report(results_dir, summary, analysis_name, scale_value)
            
            # Вывод итогов
            self._print_summary(summary, results_dir)
            
            self.stdout.write(
                self.style.SUCCESS(f'Анализ завершен! Результаты сохранены в: {results_dir}')
            )
            
        except Exception as e:
            # Обновление статуса в БД в случае ошибки
            if save_to_db and 'analysis' in locals() and analysis:
                analysis.status = 'failed'
                analysis.error_message = str(e)
                analysis.save()
            
            raise CommandError(f'Ошибка при выполнении анализа: {e}')

    def _get_image_files(self, path: Path, formats: List[str]) -> List[Path]:
        """Получение списка файлов изображений"""
        image_files = []
        
        if path.is_file():
            if any(path.name.lower().endswith(fmt.lower()) for fmt in formats):
                image_files.append(path)
        elif path.is_dir():
            for fmt in formats:
                image_files.extend(path.glob(f'*{fmt}'))
                image_files.extend(path.glob(f'*{fmt.upper()}'))
        
        return sorted(image_files)

    def _get_or_create_user(self, user_id: int = None) -> User:
        """Получение или создание пользователя"""
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f'Пользователь с ID {user_id} не найден')
        else:
            # Создание или получение системного пользователя
            user, created = User.objects.get_or_create(
                username='system_porosity_analyzer',
                defaults={
                    'email': 'system@porosity.local',
                    'first_name': 'System',
                    'last_name': 'Porosity Analyzer'
                }
            )
            if created:
                self.stdout.write('Создан системный пользователь для анализа')
            return user

    def _save_image_to_db(self, analysis: PorosityAnalysis, image_file: Path, results: Dict):
        """Сохранение изображения в базу данных"""
        try:
            with open(image_file, 'rb') as f:
                image_content = ContentFile(f.read(), name=image_file.name)
                
            porosity_image = PorosityImage.objects.create(
                analysis=analysis,
                original_image=image_content,
                filename=image_file.name,
                image_porosity_percentage=results.get('porosity_percentage'),
                image_number_of_pores=results.get('number_of_pores'),
                image_average_pore_diameter=results.get('average_pore_diameter_microns')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Не удалось сохранить изображение в БД: {e}')
            )

    def _print_image_results(self, filename: str, results: Dict):
        """Вывод результатов анализа изображения"""
        self.stdout.write(f'  Результаты для {filename}:')
        self.stdout.write(f'    Пористость: {results.get("porosity_percentage", "N/A"):.2f}%')
        self.stdout.write(f'    Количество пор: {results.get("number_of_pores", "N/A")}')
        self.stdout.write(f'    Средний диаметр пор: {results.get("average_pore_diameter_microns", "N/A"):.2f} мкм')
        self.stdout.write(f'    Общая площадь пор: {results.get("total_pore_area_microns", "N/A"):.2f} мкм²')

    def _calculate_summary(self, all_results: List[Dict]) -> Dict:
        """Расчет сводных результатов"""
        if not all_results:
            return {}
        
        total_porosity = sum(r.get('porosity_percentage', 0) for r in all_results)
        total_pores = sum(r.get('number_of_pores', 0) for r in all_results)
        total_diameter = sum(r.get('average_pore_diameter_microns', 0) for r in all_results)
        total_area = sum(r.get('total_pore_area_microns', 0) for r in all_results)
        
        num_images = len(all_results)
        
        return {
            'average_porosity_percentage': total_porosity / num_images,
            'total_number_of_pores': total_pores,
            'average_pore_diameter': total_diameter / num_images,
            'total_pore_area': total_area,
            'number_of_images': num_images
        }

    def _update_analysis_results(
        self, 
        analysis: PorosityAnalysis, 
        summary: Dict, 
        all_results: List[Dict],
        results_dir: Path
    ):
        """Обновление результатов анализа в БД"""
        try:
            # Обновление основных результатов
            analysis.porosity_percentage = summary['average_porosity_percentage']
            analysis.number_of_pores = summary['total_number_of_pores']
            analysis.average_pore_diameter = summary['average_pore_diameter']
            analysis.total_pore_area = summary['total_pore_area']
            analysis.status = 'completed'
            analysis.save()
            
            # Сохранение детальных результатов
            combined_results = self._combine_detailed_results(all_results)
            PorosityResults.objects.update_or_create(
                analysis=analysis,
                defaults=combined_results
            )
            
            # Сохранение визуализаций
            self._save_visualizations_to_db(analysis, results_dir)
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Не удалось обновить результаты в БД: {e}')
            )

    def _combine_detailed_results(self, all_results: List[Dict]) -> Dict:
        """Объединение детальных результатов"""
        combined = {
            'pore_size_distribution': [],
            'interpore_distances': [],
            'pore_orientation': [],
            'pore_shapes': [],
            'scale_info': [],
            'excluded_areas': []
        }
        
        for results in all_results:
            for key in combined.keys():
                if key in results and results[key] is not None:
                    if isinstance(results[key], list):
                        combined[key].extend(results[key])
                    else:
                        combined[key].append(results[key])
        
        return combined

    def _save_visualizations_to_db(self, analysis: PorosityAnalysis, results_dir: Path):
        """Сохранение путей к визуализациям в БД"""
        file_mappings = {
            'scale_bar.png': 'scale_bar',
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
        
        for subdir in results_dir.glob('image_*'):
            if subdir.is_dir():
                for filename, viz_type in file_mappings.items():
                    file_path = subdir / filename
                    if file_path.exists():
                        PorosityVisualization.objects.get_or_create(
                            analysis=analysis,
                            visualization_type=viz_type,
                            defaults={'file_path': str(file_path)}
                        )

    def _save_summary_report(
        self, 
        results_dir: Path, 
        summary: Dict, 
        analysis_name: str,
        scale_value: float
    ):
        """Сохранение сводного отчета"""
        report_path = results_dir / 'summary_report.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"ОТЧЕТ ПО АНАЛИЗУ ПОРИСТОСТИ\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"Название анализа: {analysis_name}\n")
            f.write(f"Значение шкалы: {scale_value} мкм\n")
            f.write(f"Количество изображений: {summary.get('number_of_images', 0)}\n\n")
            
            f.write("СВОДНЫЕ РЕЗУЛЬТАТЫ:\n")
            f.write(f"- Средняя пористость: {summary.get('average_porosity_percentage', 0):.2f}%\n")
            f.write(f"- Общее количество пор: {summary.get('total_number_of_pores', 0)}\n")
            f.write(f"- Средний диаметр пор: {summary.get('average_pore_diameter', 0):.2f} мкм\n")
            f.write(f"- Общая площадь пор: {summary.get('total_pore_area', 0):.2f} мкм²\n")

    def _print_summary(self, summary: Dict, results_dir: Path):
        """Вывод сводных результатов"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('СВОДНЫЕ РЕЗУЛЬТАТЫ АНАЛИЗА'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'Количество обработанных изображений: {summary.get("number_of_images", 0)}')
        self.stdout.write(f'Средняя пористость: {summary.get("average_porosity_percentage", 0):.2f}%')
        self.stdout.write(f'Общее количество пор: {summary.get("total_number_of_pores", 0)}')
        self.stdout.write(f'Средний диаметр пор: {summary.get("average_pore_diameter", 0):.2f} мкм')
        self.stdout.write(f'Общая площадь пор: {summary.get("total_pore_area", 0):.2f} мкм²')
        self.stdout.write(f'Результаты сохранены в: {results_dir}') 