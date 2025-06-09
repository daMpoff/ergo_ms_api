import os
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Any

from celery import shared_task
from django.conf import settings

from src.external.porosity_analysis.models import PorosityAnalysis, PorosityImage, PorosityResults, PorosityVisualization
from src.external.porosity_analysis.scripts.porosity_analyzer import PorosityAnalyzer


@shared_task(bind=True)
def process_porosity_analysis(self, analysis_id: str, images_data: List[Dict]):
    """
    Асинхронная задача для обработки анализа пористости
    
    Args:
        analysis_id: ID анализа
        images_data: Список данных изображений
    """
    try:
        # Получение анализа
        analysis = PorosityAnalysis.objects.get(id=analysis_id)
        analysis.status = 'processing'
        analysis.save()
        
        # Создание директории для результатов
        results_dir = _create_results_directory(analysis_id)
        analysis.results_directory = str(results_dir)
        analysis.save()
        
        # Инициализация анализатора
        analyzer = PorosityAnalyzer()
        
        # Обработка каждого изображения
        all_results = []
        total_porosity = 0
        total_pores = 0
        total_diameter = 0
        total_area = 0
        
        for i, image_data in enumerate(images_data):
            self.update_state(
                state='PROGRESS',
                meta={'current': i, 'total': len(images_data), 'stage': 'processing_images'}
            )
            
            image_results = _process_single_image(
                analyzer, image_data, analysis.scale_value, results_dir, i
            )
            
            if image_results:
                all_results.append(image_results)
                
                # Обновление результатов изображения
                _update_image_results(image_data['id'], image_results)
                
                # Накопление статистики
                total_porosity += image_results.get('porosity_percentage', 0)
                total_pores += image_results.get('number_of_pores', 0)
                total_diameter += image_results.get('average_pore_diameter_microns', 0)
                total_area += image_results.get('total_pore_area_microns', 0)
        
        # Усреднение результатов
        if all_results:
            num_images = len(all_results)
            analysis.porosity_percentage = total_porosity / num_images
            analysis.number_of_pores = total_pores
            analysis.average_pore_diameter = total_diameter / num_images
            analysis.total_pore_area = total_area
        
        # Сохранение детальных результатов
        _save_detailed_results(analysis, all_results)
        
        # Сохранение путей к визуализациям
        _save_visualizations(analysis, results_dir)
        
        # Завершение анализа
        analysis.status = 'completed'
        analysis.save()
        
        return {
            'status': 'completed',
            'porosity_percentage': analysis.porosity_percentage,
            'number_of_pores': analysis.number_of_pores
        }
        
    except Exception as e:
        # Обработка ошибок
        try:
            analysis = PorosityAnalysis.objects.get(id=analysis_id)
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
        except:
            pass
        
        # Логирование ошибки
        print(f"Ошибка при обработке анализа {analysis_id}: {e}")
        traceback.print_exc()
        
        raise e


def _create_results_directory(analysis_id: str) -> Path:
    """Создание директории для результатов анализа"""
    media_root = Path(settings.MEDIA_ROOT)
    results_dir = media_root / 'porosity_results' / analysis_id
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def _process_single_image(
    analyzer: PorosityAnalyzer, 
    image_data: Dict, 
    scale_value: float,
    results_dir: Path,
    image_index: int
) -> Dict[str, Any]:
    """Обработка одного изображения"""
    try:
        image_path = image_data['path']
        
        # Создание поддиректории для изображения
        image_results_dir = results_dir / f"image_{image_index}_{image_data['filename']}"
        image_results_dir.mkdir(exist_ok=True)
        
        # Запуск анализа
        results = analyzer.integrated_analysis(
            image_path, 
            scale_value, 
            str(image_results_dir)
        )
        
        return results
        
    except Exception as e:
        print(f"Ошибка при обработке изображения {image_data['filename']}: {e}")
        return None


def _update_image_results(image_id: int, results: Dict[str, Any]):
    """Обновление результатов для конкретного изображения"""
    try:
        image = PorosityImage.objects.get(id=image_id)
        image.image_porosity_percentage = results.get('porosity_percentage')
        image.image_number_of_pores = results.get('number_of_pores')
        image.image_average_pore_diameter = results.get('average_pore_diameter_microns')
        image.save()
    except Exception as e:
        print(f"Ошибка при обновлении результатов изображения {image_id}: {e}")


def _save_detailed_results(analysis: PorosityAnalysis, all_results: List[Dict[str, Any]]):
    """Сохранение детальных результатов анализа"""
    try:
        # Объединение результатов всех изображений
        combined_results = _combine_results(all_results)
        
        # Создание или обновление детальных результатов
        detailed_results, created = PorosityResults.objects.get_or_create(
            analysis=analysis,
            defaults=combined_results
        )
        
        if not created:
            for key, value in combined_results.items():
                setattr(detailed_results, key, value)
            detailed_results.save()
            
    except Exception as e:
        print(f"Ошибка при сохранении детальных результатов: {e}")


def _combine_results(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Объединение результатов всех изображений"""
    combined = {
        'pore_size_distribution': [],
        'interpore_distances': [],
        'pore_orientation': [],
        'pore_shapes': [],
        'scale_info': [],
        'excluded_areas': []
    }
    
    for results in all_results:
        if 'pore_size_distribution' in results:
            combined['pore_size_distribution'].append(results['pore_size_distribution'])
        if 'interpore_distances' in results:
            combined['interpore_distances'].extend(results.get('interpore_distances', []))
        if 'pore_orientation' in results:
            combined['pore_orientation'].append(results['pore_orientation'])
        if 'pore_shapes' in results:
            combined['pore_shapes'].append(results['pore_shapes'])
        if 'scale_info' in results:
            combined['scale_info'].append({
                'pixels_per_micron': results.get('pixels_per_micron'),
                'scale_region': results.get('scale_region')
            })
        if 'excluded_areas' in results:
            combined['excluded_areas'].append(results.get('excluded_areas', {}))
    
    return combined


def _save_visualizations(analysis: PorosityAnalysis, results_dir: Path):
    """Сохранение путей к визуализациям"""
    try:
        # Mapping файлов к типам визуализации
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
        
        # Поиск и сохранение визуализаций из всех поддиректорий
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
        
    except Exception as e:
        print(f"Ошибка при сохранении визуализаций: {e}")


@shared_task
def cleanup_old_results():
    """Задача для очистки старых результатов анализа"""
    from datetime import datetime, timedelta
    
    # Удаление результатов старше 30 дней
    cutoff_date = datetime.now() - timedelta(days=30)
    old_analyses = PorosityAnalysis.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed']
    )
    
    for analysis in old_analyses:
        try:
            # Удаление файлов
            if analysis.results_directory:
                results_dir = Path(analysis.results_directory)
                if results_dir.exists():
                    import shutil
                    shutil.rmtree(results_dir)
            
            # Удаление записи
            analysis.delete()
            
        except Exception as e:
            print(f"Ошибка при очистке анализа {analysis.id}: {e}")
    
    return f"Очищено {old_analyses.count()} старых анализов" 