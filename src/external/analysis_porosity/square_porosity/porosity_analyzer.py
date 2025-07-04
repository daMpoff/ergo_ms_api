"""
Основной модуль анализа пористости изображений микроскопии
"""
import os
import cv2
import traceback
from typing import Dict, Any, Optional

# Настройка Matplotlib для работы без GUI (для фоновых процессов)
import matplotlib
matplotlib.use('Agg')

import numpy as np

from src.external.analysis_porosity.square_porosity.preprocessing import detect_scale_bar
from src.external.analysis_porosity.square_porosity.core_analysis import advanced_porosity_analysis
from src.external.analysis_porosity.square_porosity.calculations import (
    calculate_pore_size_distribution,
    calculate_interpore_distances,
    calculate_pore_orientation,
    calculate_pore_shapes
)
from src.external.analysis_porosity.square_porosity.visualization import (
    visualize_porosity_analysis_stages,
    visualize_pore_size_distribution,
    visualize_interpore_distances,
    visualize_pore_orientation,
    visualize_pore_shapes
)
from src.external.analysis_porosity.square_porosity.config import FILES, MESSAGES
from src.external.analysis_porosity.square_porosity.utils import calculate_basic_pore_statistics


class PorosityAnalyzer:
    """Главный класс для анализа пористости изображений микроскопии"""
    
    def __init__(self):
        self.config_files = FILES
        self.messages = MESSAGES
    
    def analyze_porosity(
        self, 
        image_path: str, 
        scale_value: float, 
        output_dir: str
    ) -> Optional[Dict[str, Any]]:
        """
        Анализ пористости для использования в задачах Celery
        
        Args:
            image_path: Путь к изображению
            scale_value: Значение шкалы в микрометрах
            output_dir: Директория для сохранения результатов
            
        Returns:
            Результаты анализа в формате для сохранения в БД или None в случае ошибки
        """
        try:
            print(f"analyze_porosity получил output_dir: {output_dir}")
            print(f"Абсолютный путь: {os.path.abspath(output_dir)}")
            print(f"Текущая рабочая директория: {os.getcwd()}")
            print(f"Переменная окружения TMPDIR: {os.environ.get('TMPDIR', 'Не установлена')}")
            print(f"Переменная окружения TEMP: {os.environ.get('TEMP', 'Не установлена')}")
            # Выполняем интегрированный анализ
            results = self.integrated_analysis(image_path, scale_value, output_dir)
            
            if results is None:
                return None
            
            # Преобразуем результаты в формат для сохранения в БД
            db_results = {
                'porosity_percentage': results.get('porosity_percentage', 0.0),
                'relative_pore_area': results.get('relative_pore_area', 0.0),
                'number_of_pores': results.get('number_of_pores', 0),
                'mean_pore_size_microns': results.get('mean_pore_size_microns', 0.0),
                'median_pore_size_microns': results.get('median_pore_size_microns', 0.0),
                'mean_pore_diameter_microns': results.get('mean_pore_diameter_microns', 0.0),
                'median_pore_diameter_microns': results.get('median_pore_diameter_microns', 0.0),
                'pixels_per_micron': results.get('pixels_per_micron', 0.0),
                'scale_region_x': results.get('scale_region', (0, 0, 0, 0))[0],
                'scale_region_y': results.get('scale_region', (0, 0, 0, 0))[1],
                'scale_region_width': results.get('scale_region', (0, 0, 0, 0))[2],
                'scale_region_height': results.get('scale_region', (0, 0, 0, 0))[3],
                'total_pixels': results.get('total_pixels', 0),
                'scale_excluded_pixels': results.get('scale_excluded_pixels', 0),
                'lines_excluded_pixels': results.get('lines_excluded_pixels', 0),
                'anomalies_excluded_pixels': results.get('anomalies_excluded_pixels', 0),
                'total_excluded_pixels': results.get('total_excluded_pixels', 0),
                'extended_metrics': {
                    'pore_size_distribution': results.get('pore_size_distribution', {}),
                    'interpore_distances': results.get('interpore_distances', {}),
                    'pore_orientation': results.get('pore_orientation', {}),
                    'pore_shapes': results.get('pore_shapes', {}),
                    'pore_centers': results.get('pore_centers', [])
                }
            }
            
            return db_results
            
        except Exception as e:
            print(f"Ошибка при анализе пористости: {e}")
            import traceback
            traceback.print_exc()
            return None

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
            print(f"Анализатор получил директорию для сохранения: {save_directory}")
            print(f"Абсолютный путь: {os.path.abspath(save_directory)}")
            # 1. Определение масштаба по линейке
            scale_results = self._detect_scale(image_path, scale_value, save_directory)
            pixels_per_micron, scale_result, scale_region = scale_results
            microns_per_pixel = 1.0 / pixels_per_micron
            
            self._log_scale_detection(pixels_per_micron, microns_per_pixel, scale_region)
            self._save_scale_image(scale_result, save_directory)
            
            # 2. Анализ пористости с учетом масштаба
            core_results = advanced_porosity_analysis(
                image_path, pixels_per_micron, scale_region, save_directory
            )
            
            # 3. Дополнительные расчеты
            additional_results = self._perform_additional_calculations(
                core_results, microns_per_pixel
            )
            
            # 4. Объединение результатов
            results = {**core_results, **additional_results}
            
            # 5. Создание визуализаций
            self._create_visualizations(results, save_directory)
            
            # 6. Вывод итоговых результатов
            self._log_final_results(results)
            
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
        """Логирует результаты детекции масштаба"""
        print(self.messages['SCALE_DETECTED'])
        print(f"1 пиксель = {microns_per_pixel:.5f} мкм")
        print(f"1 мкм = {pixels_per_micron:.5f} пикселей")
        print(f"Область линейки: x={scale_region[0]}, y={scale_region[1]}, "
              f"ширина={scale_region[2]}, высота={scale_region[3]}")
    
    def _save_scale_image(self, scale_result: np.ndarray, save_directory: str) -> None:
        """Сохраняет изображение с обнаруженной линейкой"""
        filename = self.config_files['IMAGE_WITH_SCALE_FILENAME']
        output_path = os.path.join(save_directory, filename)
        print(f"Сохраняем изображение с линейкой в: {output_path}")
        cv2.imwrite(output_path, scale_result)
        
        if os.path.exists(output_path):
            print(f"Изображение с линейкой успешно сохранено: {output_path}")
        else:
            print(f"ОШИБКА: Изображение с линейкой не сохранено: {output_path}")
    
    def _perform_additional_calculations(
        self, 
        core_results: Dict[str, Any], 
        microns_per_pixel: float
    ) -> Dict[str, Any]:
        """Выполняет дополнительные расчеты"""
        print(f"\n{self.messages['CALCULATIONS_START']}")
        
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
        """Создает все визуализации"""
        print(f"\n{self.messages['VISUALIZATIONS_START']}")
        
        try:
            print(f"Начинаем создание визуализаций в директории: {save_directory}")
            print(f"Абсолютный путь: {os.path.abspath(save_directory)}")
            
            # Проверяем существование директории
            if not os.path.exists(save_directory):
                print(f"Создаем директорию для сохранения: {save_directory}")
                os.makedirs(save_directory, exist_ok=True)
            
            print(f"Директория для сохранения: {save_directory}")
            
            # Создаем задачи визуализации
            visualization_tasks = self._create_visualization_tasks(results, save_directory)
            
            print(f"Создано {len(visualization_tasks)} задач визуализации")
            
            # Выполняем все визуализации
            for i, task in enumerate(visualization_tasks):
                try:
                    print(f"Выполняем визуализацию {i+1}/{len(visualization_tasks)}")
                    task()
                    print(f"Визуализация {i+1} завершена успешно")
                except Exception as e:
                    print(f"Ошибка при выполнении визуализации {i+1}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            print(self.messages['VISUALIZATIONS_COMPLETE'])
            
        except Exception as e:
            print(f"Ошибка при создании визуализаций: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
        """Выводит итоговые результаты анализа"""
        print("\nРезультаты анализа пористости (исключая область измерительной линейки, линии и аномалии):")
        
        # Основные метрики
        self._log_main_metrics(results)
        
        # Информация об исключенных областях
        self._log_excluded_areas(results)
    
    def _log_main_metrics(self, results: Dict[str, Any]) -> None:
        """Логирует основные метрики"""
        print(f"Пористость: {results['porosity_percentage']:.2f}%")
        print(f"Относительная площадь пор: {results['relative_pore_area']:.2f}%")
        print(f"Количество пор: {results['number_of_pores']}")
        print(f"Средний размер поры: {results['mean_pore_size_microns']:.2f} мкм²")
        print(f"Медианный размер поры: {results['median_pore_size_microns']:.2f} мкм²")
        print(f"Средний диаметр поры: {results['mean_pore_diameter_microns']:.2f} мкм")
        print(f"Медианный диаметр поры: {results['median_pore_diameter_microns']:.2f} мкм")
    
    def _log_excluded_areas(self, results: Dict[str, Any]) -> None:
        """Логирует информацию об исключенных областях"""
        total_pixels = results['gray'].size
        
        # Подсчет исключенных областей
        scale_excluded = np.sum(~results['scale_exclude_mask'])
        lines_excluded = np.sum(~results['lines_exclude_mask'])
        anomalies_excluded = np.sum(~results['anomalies_exclude_mask'])
        total_excluded = np.sum(~results['exclude_mask'])
        
        print(f"\nИсключенные области:")
        print(f"Область шкалы: {scale_excluded} пикселей ({(scale_excluded/total_pixels)*100:.2f}%)")
        print(f"Области линий: {lines_excluded} пикселей ({(lines_excluded/total_pixels)*100:.2f}%)")
        print(f"Аномальные области: {anomalies_excluded} пикселей ({(anomalies_excluded/total_pixels)*100:.2f}%)")
        print(f"Общая исключенная область: {total_excluded} пикселей ({(total_excluded/total_pixels)*100:.2f}%)")
        print(f"Область анализа: {total_pixels - total_excluded} пикселей ({((total_pixels - total_excluded)/total_pixels)*100:.2f}%)")


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