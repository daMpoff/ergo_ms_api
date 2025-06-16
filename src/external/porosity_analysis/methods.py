"""
Django-обертка для методов анализа пористости
"""
import os
import sys
from pathlib import Path

# Добавление пути к скриптам анализа
SCRIPTS_DIR = Path(__file__).parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from src.external.porosity_analysis.scripts.porosity_analyzer import PorosityAnalyzer as BasePorosityAnalyzer


class PorosityAnalyzer(BasePorosityAnalyzer):
    """Django-адаптер для анализатора пористости"""
    
    def __init__(self):
        super().__init__()
    
    def analyze_image(self, image_path: str, scale_value: float, output_dir: str):
        """
        Анализ одного изображения с возвратом структурированных результатов
        
        Args:
            image_path: Путь к изображению
            scale_value: Значение шкалы в микрометрах
            output_dir: Директория для сохранения результатов
            
        Returns:
            dict: Результаты анализа или None в случае ошибки
        """
        try:
            return self.integrated_analysis(image_path, scale_value, output_dir)
        except Exception as e:
            print(f"Ошибка при анализе изображения {image_path}: {e}")
            return None
    
    def get_available_visualizations(self):
        """Возвращает список доступных типов визуализации"""
        return [
            'scale_bar',
            'contrast_stages', 
            'excluded_areas',
            'texture_clusters',
            'mask_result',
            'overlay',
            'pore_size_distribution',
            'interpore_distances',
            'pore_orientation_rose',
            'pore_orientation_histogram',
            'pore_shapes_analysis',
            'circularity_distribution',
            'ellipticity_vs_area',
        ]