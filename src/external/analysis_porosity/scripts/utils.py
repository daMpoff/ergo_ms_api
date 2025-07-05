"""
Вспомогательные утилиты для анализа пористости
"""
import numpy as np
from typing import List, Dict, Any, Tuple
from skimage.measure import regionprops


def vectorized_equivalent_diameter(areas: np.ndarray) -> np.ndarray:
    """
    Векторизованное вычисление диаметра эквивалентного круга.
    
    Args:
        areas: Массив площадей
        
    Returns:
        Массив диаметров эквивалентных кругов
    """
    return 2 * np.sqrt(np.array(areas) / np.pi)


def batch_process_properties(pore_properties: List, microns_per_pixel: float) -> Dict[str, np.ndarray]:
    """
    Пакетная обработка свойств пор для избежания повторных вычислений.
    
    Args:
        pore_properties: Список свойств пор от regionprops
        microns_per_pixel: Коэффициент пересчета пикселей в микрометры
        
    Returns:
        Словарь с предвычисленными массивами свойств
    """
    if not pore_properties:
        return {
            'areas_pixels': np.array([]),
            'areas_microns': np.array([]),
            'diameters_microns': np.array([]),
            'centers': np.array([]).reshape(0, 2),
            'perimeters_pixels': np.array([]),
            'perimeters_microns': np.array([]),
            'major_axes_pixels': np.array([]),
            'minor_axes_pixels': np.array([]),
            'major_axes_microns': np.array([]),
            'minor_axes_microns': np.array([]),
            'aspect_ratios': np.array([]),
            'orientations': np.array([]),
            'solidities': np.array([]),
            'eccentricities': np.array([]),
        }
    
    # Векторизованное извлечение всех нужных свойств
    areas_pixels = np.array([prop.area for prop in pore_properties])
    perimeters_pixels = np.array([prop.perimeter for prop in pore_properties])
    centers = np.array([prop.centroid for prop in pore_properties])
    major_axes_pixels = np.array([getattr(prop, 'major_axis_length', 0) for prop in pore_properties])
    minor_axes_pixels = np.array([getattr(prop, 'minor_axis_length', 1) for prop in pore_properties])  # Избегаем деления на 0
    orientations = np.array([getattr(prop, 'orientation', 0) for prop in pore_properties])
    solidities = np.array([getattr(prop, 'solidity', 1) for prop in pore_properties])
    eccentricities = np.array([getattr(prop, 'eccentricity', 0) for prop in pore_properties])
    
    # Векторизованные вычисления
    areas_microns = areas_pixels * (microns_per_pixel ** 2)
    perimeters_microns = perimeters_pixels * microns_per_pixel
    diameters_microns = vectorized_equivalent_diameter(areas_pixels) * microns_per_pixel
    major_axes_microns = major_axes_pixels * microns_per_pixel
    minor_axes_microns = minor_axes_pixels * microns_per_pixel
    
    # Безопасное вычисление соотношения сторон
    aspect_ratios = np.divide(
        major_axes_pixels, 
        minor_axes_pixels, 
        out=np.ones_like(major_axes_pixels), 
        where=(minor_axes_pixels > 0)
    )
    
    return {
        'areas_pixels': areas_pixels,
        'areas_microns': areas_microns,
        'diameters_microns': diameters_microns,
        'centers': centers,
        'perimeters_pixels': perimeters_pixels,
        'perimeters_microns': perimeters_microns,
        'major_axes_pixels': major_axes_pixels,
        'minor_axes_pixels': minor_axes_pixels,
        'major_axes_microns': major_axes_microns,
        'minor_axes_microns': minor_axes_microns,
        'aspect_ratios': aspect_ratios,
        'orientations': orientations,
        'solidities': solidities,
        'eccentricities': eccentricities,
    }


def calculate_basic_pore_statistics(batch_data: Dict[str, np.ndarray]) -> Dict[str, float]:
    """
    Вычисляет базовые статистики для пор на основе предобработанных данных.
    
    Args:
        batch_data: Предобработанные данные от batch_process_properties
        
    Returns:
        Словарь с базовыми статистиками
    """
    if len(batch_data['areas_microns']) == 0:
        return {
            'mean_pore_size_microns': 0.0,
            'median_pore_size_microns': 0.0,
            'mean_pore_diameter_microns': 0.0,
            'median_pore_diameter_microns': 0.0,
            'mean_pore_size_pixels': 0.0,
            'std_pore_size_microns': 0.0,
            'std_pore_diameter_microns': 0.0,
        }
    
    return {
        'mean_pore_size_microns': float(np.mean(batch_data['areas_microns'])),
        'median_pore_size_microns': float(np.median(batch_data['areas_microns'])),
        'mean_pore_diameter_microns': float(np.mean(batch_data['diameters_microns'])),
        'median_pore_diameter_microns': float(np.median(batch_data['diameters_microns'])),
        'mean_pore_size_pixels': float(np.mean(batch_data['areas_pixels'])),
        'std_pore_size_microns': float(np.std(batch_data['areas_microns'])),
        'std_pore_diameter_microns': float(np.std(batch_data['diameters_microns'])),
    }


def safe_divide(numerator: np.ndarray, denominator: np.ndarray, default_value: float = 0.0) -> np.ndarray:
    """
    Безопасное деление с обработкой деления на ноль.
    
    Args:
        numerator: Числитель
        denominator: Знаменатель
        default_value: Значение по умолчанию при делении на ноль
        
    Returns:
        Результат деления
    """
    return np.divide(
        numerator, 
        denominator, 
        out=np.full_like(numerator, default_value, dtype=float), 
        where=(denominator > 1e-10)
    )


def create_exclusion_mask(image_shape: Tuple[int, int], regions_to_exclude: List[Tuple[int, int, int, int]]) -> np.ndarray:
    """
    Создает маску исключения для заданных регионов.
    
    Args:
        image_shape: Форма изображения (height, width)
        regions_to_exclude: Список регионов в формате (x, y, width, height)
        
    Returns:
        Булева маска (True - включить в анализ, False - исключить)
    """
    mask = np.ones(image_shape, dtype=bool)
    
    for x, y, w, h in regions_to_exclude:
        # Проверяем границы
        y_start = max(0, y)
        y_end = min(image_shape[0], y + h)
        x_start = max(0, x)
        x_end = min(image_shape[1], x + w)
        
        mask[y_start:y_end, x_start:x_end] = False
    
    return mask


def filter_pores_by_criteria(
    pore_properties: List, 
    min_area: float = 0, 
    max_area: float = np.inf,
    min_aspect_ratio: float = 0,
    max_aspect_ratio: float = np.inf
) -> List:
    """
    Фильтрует поры по заданным критериям.
    
    Args:
        pore_properties: Список свойств пор
        min_area: Минимальная площадь
        max_area: Максимальная площадь
        min_aspect_ratio: Минимальное соотношение сторон
        max_aspect_ratio: Максимальное соотношение сторон
        
    Returns:
        Отфильтрованный список свойств пор
    """
    filtered_props = []
    
    for prop in pore_properties:
        area = prop.area
        
        # Безопасное вычисление соотношения сторон
        major_axis = getattr(prop, 'major_axis_length', 0)
        minor_axis = getattr(prop, 'minor_axis_length', 1)
        aspect_ratio = major_axis / minor_axis if minor_axis > 0 else 1
        
        # Проверка критериев
        if (min_area <= area <= max_area and 
            min_aspect_ratio <= aspect_ratio <= max_aspect_ratio):
            filtered_props.append(prop)
    
    return filtered_props


def calculate_porosity_percentage(pore_mask: np.ndarray, analysis_mask: np.ndarray) -> float:
    """
    Вычисляет процент пористости.
    
    Args:
        pore_mask: Бинарная маска пор
        analysis_mask: Маска области анализа
        
    Returns:
        Процент пористости
    """
    total_area = np.sum(analysis_mask)
    if total_area == 0:
        return 0.0
    
    pore_area = np.sum(pore_mask & analysis_mask)
    return (pore_area / total_area) * 100

 