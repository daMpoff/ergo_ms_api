"""
Основной модуль анализа пористости изображений микроскопии
"""
import os
import cv2
import traceback
from typing import Dict, Any, Optional

# Настройка Matplotlib для работы в фоновом режиме (без GUI)
# ДОЛЖНО БЫТЬ ДО ИМПОРТА matplotlib
import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend

import numpy as np

from src.modules.porosity_analysis.scripts.preprocessing import detect_scale_bar
from src.modules.porosity_analysis.scripts.core_analysis import advanced_porosity_analysis
from src.modules.porosity_analysis.scripts.calculations import (
    calculate_pore_size_distribution,
    calculate_interpore_distances,
    calculate_pore_orientation,
    calculate_pore_shapes
)
from src.modules.porosity_analysis.scripts.visualization import (
    visualize_porosity_analysis_stages,
    visualize_pore_size_distribution,
    visualize_interpore_distances,
    visualize_pore_orientation,
    visualize_pore_shapes
)
from src.modules.porosity_analysis.scripts.config import FILES, MESSAGES
from src.modules.porosity_analysis.scripts.utils import calculate_basic_pore_statistics
from src.modules.porosity_analysis.utils import is_cancelled


class PorosityAnalyzer:
    """Главный класс для анализа пористости изображений микроскопии"""
    
    def __init__(self):
        self.config_files = FILES
        self.messages = MESSAGES
        self.last_results = None
    
    def integrated_analysis(
        self, 
        image_path: str, 
        scale_value: float, 
        save_directory: str
    ) -> Optional[Dict[str, Any]]:
        """
        Интегрированный анализ пористости с автоматическим определением масштаба
        
        Args:
            image_path: Путь к изображению
            scale_value: Значение шкалы в микрометрах
            save_directory: Директория для сохранения результатов
            
        Returns:
            Результаты анализа или None в случае ошибки
        """
        try:
            # Ранняя проверка отмены
            analysis_id_env = os.environ.get('POROSITY_ANALYSIS_ID')
            if analysis_id_env and is_cancelled(int(analysis_id_env)):
                print(f"Задача анализа {analysis_id_env} отменена до выполнения. Выход.")
                return None
            # 1. Определение масштаба по линейке
            scale_results = self._detect_scale(image_path, scale_value, save_directory)
            pixels_per_micron, scale_result, scale_region = scale_results
            microns_per_pixel = 1.0 / pixels_per_micron
            
            self._log_scale_detection(pixels_per_micron, microns_per_pixel, scale_region)
            self._save_scale_image(scale_result, save_directory)
            
            # 2. Анализ пористости с учетом масштаба
            # Проверка отмены перед тяжелым этапом
            analysis_id_env = os.environ.get('POROSITY_ANALYSIS_ID')
            if analysis_id_env and is_cancelled(int(analysis_id_env)):
                print(f"Задача анализа {analysis_id_env} отменена перед основным этапом. Выход.")
                return None

            core_results = advanced_porosity_analysis(
                image_path, pixels_per_micron, scale_region, save_directory
            )
            
            # 3. Дополнительные расчеты
            additional_results = self._perform_additional_calculations(
                core_results, microns_per_pixel
            )
            
            # 4. Объединение результатов
            results = {**core_results, **additional_results}
            
            # Добавляем информацию о масштабе
            results['pixels_per_micron'] = pixels_per_micron
            results['microns_per_pixel'] = microns_per_pixel
            
            # 5. Создание визуализаций (с проверкой отмены)
            analysis_id_env = os.environ.get('POROSITY_ANALYSIS_ID')
            if analysis_id_env and is_cancelled(int(analysis_id_env)):
                print(f"Задача анализа {analysis_id_env} отменена перед визуализациями. Выход.")
                return None
            self._create_visualizations(results, save_directory)
            
            # 6. Вывод итоговых результатов
            self._log_final_results(results)
            
            # Сохраняем результаты для последующего доступа
            self.last_results = results
            
            return results
            
        except Exception as e:
            print(f"Ошибка при анализе изображения: {e}")
            traceback.print_exc()
            return None
    
    def _detect_scale(self, image_path: str, scale_value: float, save_directory: str) -> tuple:
        """Обнаруживает масштаб по линейке"""
        return detect_scale_bar(image_path, scale_value, save_directory)
    
    def _log_scale_detection(
        self, 
        pixels_per_micron: float, 
        microns_per_pixel: float,
        scale_region: tuple
    ) -> None:
        """Логирует результаты детекции масштаба (приглушено для Celery)."""
        pass
    
    def _save_scale_image(self, scale_result: np.ndarray, save_directory: str) -> None:
        """Сохраняет изображение с обнаруженной линейкой"""
        filename = self.config_files['IMAGE_WITH_SCALE_FILENAME']
        cv2.imwrite(os.path.join(save_directory, filename), scale_result)
    
    def _perform_additional_calculations(
        self, 
        core_results: Dict[str, Any], 
        microns_per_pixel: float
    ) -> Dict[str, Any]:
        """Выполняет дополнительные расчеты (без избыточного вывода)."""
        
        pore_properties = core_results['pore_properties']
        pore_diameters_microns = core_results['pore_diameters_microns']
        
        # Группируем расчеты для оптимизации
        calculations = self._create_calculation_tasks(
            pore_properties, pore_diameters_microns, microns_per_pixel
        )
        
        # Выполняем все расчеты
        return self._execute_calculations(calculations)
    
    def _create_calculation_tasks(
        self, 
        pore_properties: list, 
        pore_diameters_microns: list,
        microns_per_pixel: float
    ) -> dict:
        """Создает задачи для расчетов"""
        return {
            'pore_size_distribution': lambda: calculate_pore_size_distribution(
                pore_properties, pore_diameters_microns, microns_per_pixel
            ),
            'interpore_distances_and_centers': lambda: calculate_interpore_distances(
                pore_properties, microns_per_pixel
            ),
            'pore_orientation': lambda: calculate_pore_orientation(
                pore_properties, microns_per_pixel
            ),
            'pore_shapes': lambda: calculate_pore_shapes(
                pore_properties, microns_per_pixel
            )
        }
    
    def _execute_calculations(self, calculations: dict) -> Dict[str, Any]:
        """Выполняет все расчеты"""
        results = {}
        
        # Распределение пор по размерам
        results['pore_size_distribution'] = calculations['pore_size_distribution']()
        
        # Межпоровые расстояния
        interpore_distances, pore_centers = calculations['interpore_distances_and_centers']()
        results['interpore_distances'] = interpore_distances
        results['pore_centers'] = pore_centers
        
        # Ориентация и форма пор
        results['pore_orientation'] = calculations['pore_orientation']()
        results['pore_shapes'] = calculations['pore_shapes']()
        
        return results
    
    def _create_visualizations(self, results: Dict[str, Any], save_directory: str) -> None:
        """Создает все визуализации (без избыточного вывода)."""
        
        # Создаем задачи визуализации
        visualization_tasks = self._create_visualization_tasks(results, save_directory)
        
        # Выполняем все визуализации
        for task in visualization_tasks:
            task()
        
        # Приглушаем подробный вывод
    
    def _create_visualization_tasks(
        self, 
        results: Dict[str, Any], 
        save_directory: str
    ) -> list:
        """Создает задачи для визуализации"""
        return [
            # Основные этапы анализа
            lambda: visualize_porosity_analysis_stages(
                results['gray'], results['enhanced'], results['texture'], 
                results['segmented'], results['binary_mask'], results['labeled_pores'],
                results['scale_region'], results['porosity_percentage'], results['number_of_pores'],
                results['exclude_mask'], results['lines_exclude_mask'], 
                results['anomalies_exclude_mask'], results['scale_exclude_mask'], save_directory
            ),
            # Остальные визуализации
            lambda: visualize_pore_size_distribution(
                results['pore_size_distribution'], save_directory
            ),
            lambda: visualize_interpore_distances(
                results['interpore_distances'], results['pore_centers'], 
                1.0 / results.get('pixels_per_micron', 1), save_directory
            ),
            lambda: visualize_pore_orientation(
                results['pore_orientation'], save_directory
            ),
            lambda: visualize_pore_shapes(
                results['pore_shapes'], save_directory
            )
        ]
    
    def _log_final_results(self, results: Dict[str, Any]) -> None:
        """Выводит итоговые результаты анализа (приглушено для Celery)."""
        return
        
        # Основные метрики
        self._log_main_metrics(results)
        
        # Информация об исключенных областях
        self._log_excluded_areas(results)
    
    def _log_main_metrics(self, results: Dict[str, Any]) -> None:
        """Логирует основные метрики (приглушено)."""
        return
    
    def _log_excluded_areas(self, results: Dict[str, Any]) -> None:
        """Логирует информацию об исключенных областях"""
        total_pixels = results['gray'].size
        
        # Подсчет исключенных областей
        scale_excluded = np.sum(~results['scale_exclude_mask'])
        lines_excluded = np.sum(~results['lines_exclude_mask'])
        anomalies_excluded = np.sum(~results['anomalies_exclude_mask'])
        total_excluded = np.sum(~results['exclude_mask'])
        
        # Приглушаем подробные распечатки
        return
    
    def get_last_results(self):
        """Возвращает результаты последнего анализа"""
        return self.last_results


# Функция обратной совместимости
def integrated_analysis(image_path: str, scale_value: float, save_directory: str) -> Optional[Dict[str, Any]]:
    """
    Функция обратной совместимости для интегрированного анализа пористости
    
    Args:
        image_path: Путь к изображению
        scale_value: Значение шкалы в микрометрах
        save_directory: Директория для сохранения результатов
        
    Returns:
        Результаты анализа
    """
    analyzer = PorosityAnalyzer()
    return analyzer.integrated_analysis(image_path, scale_value, save_directory) 