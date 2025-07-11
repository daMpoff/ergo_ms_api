"""
Модуль для расчетов характеристик пористости
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

from scipy.spatial.distance import pdist, squareform
from scipy.stats import circmean, circstd
from sklearn.cluster import DBSCAN

from src.modules.porosity_analysis.scripts.config import (
    SIZE_ANALYSIS, CLUSTERING, ORIENTATION_ANALYSIS, SHAPE_ANALYSIS
)
from src.modules.porosity_analysis.scripts.utils import (
    vectorized_equivalent_diameter, batch_process_properties, safe_divide
)


class PorosityCalculator:
    """Класс для выполнения расчетов характеристик пористости"""
    
    def __init__(self):
        self.size_config = SIZE_ANALYSIS
        self.cluster_config = CLUSTERING
        self.orientation_config = ORIENTATION_ANALYSIS
        self.shape_config = SHAPE_ANALYSIS
    
    def calculate_pore_size_distribution(
        self, 
        pore_properties: List, 
        pore_diameters_microns: List[float], 
        microns_per_pixel: float
    ) -> pd.DataFrame:
        """
        Разбивает поры на интервалы по размерам и вычисляет статистику.
        
        Args:
            pore_properties: Список свойств пор
            pore_diameters_microns: Список диаметров пор в микрометрах
            microns_per_pixel: Соотношение микрометров к пикселям
            
        Returns:
            DataFrame с распределением пор
        """
        if not pore_diameters_microns:
            return pd.DataFrame()
        
        # Подготовка данных
        diameters_array = np.array(pore_diameters_microns)
        areas_pixels = np.array([prop.area for prop in pore_properties])
        areas_microns = areas_pixels * (microns_per_pixel ** 2)
        
        # Расчет объемов
        radii_microns = diameters_array / 2
        volumes_microns = (4/3) * np.pi * (radii_microns ** 3)
        
        # Создание интервалов
        bin_count = self.size_config['SIZE_DISTRIBUTION_BINS']
        bin_edges, bin_labels = self._create_size_bins(diameters_array, bin_count)
        
        # Распределение пор по интервалам
        pore_bins = np.digitize(diameters_array, bin_edges[1:])
        
        # Сбор статистики по интервалам
        return self._collect_size_statistics(
            pore_bins, bin_labels, areas_microns, volumes_microns
        )
    
    def calculate_interpore_distances(
        self, 
        pore_properties: List, 
        microns_per_pixel: float
    ) -> Tuple[Optional[np.ndarray], np.ndarray]:
        """
        Вычисляет межпоровые расстояния.
        
        Args:
            pore_properties: Список свойств пор
            microns_per_pixel: Соотношение микрометров к пикселям
            
        Returns:
            Кортеж: (массив расстояний в микрометрах, центры пор)
        """
        if len(pore_properties) < 2:
            centers = np.array([prop.centroid for prop in pore_properties]) if pore_properties else np.array([])
            return None, centers
        
        centers = np.array([prop.centroid for prop in pore_properties])
        
        # Матрица расстояний
        distances_matrix = squareform(pdist(centers))
        np.fill_diagonal(distances_matrix, np.inf)
        
        # Минимальные расстояния
        min_distances_pixels = np.min(distances_matrix, axis=1)
        min_distances_microns = min_distances_pixels * microns_per_pixel
        
        return min_distances_microns, centers
    
    def calculate_pore_clusters(
        self, 
        pore_properties: List, 
        microns_per_pixel: float,
        min_samples: Optional[int] = None,
        eps_microns: Optional[float] = None
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[Dict]]:
        """
        Идентифицирует группы скопления пор с использованием DBSCAN.
        
        Args:
            pore_properties: Список свойств пор
            microns_per_pixel: Соотношение микрометров к пикселям
            min_samples: Минимальное количество пор для формирования кластера
            eps_microns: Максимальное расстояние между порами в одном кластере
            
        Returns:
            Кортеж: (метки кластеров, центры пор, статистика кластеров)
        """
        if min_samples is None:
            min_samples = self.cluster_config['DBSCAN_MIN_SAMPLES']
        if eps_microns is None:
            eps_microns = self.cluster_config['DBSCAN_EPS_MICRONS']
            
        if len(pore_properties) < min_samples:
            return None, None, None
        
        centers = np.array([prop.centroid for prop in pore_properties])
        eps_pixels = eps_microns / microns_per_pixel
        
        # DBSCAN кластеризация
        db = DBSCAN(eps=eps_pixels, min_samples=min_samples).fit(centers)
        labels = db.labels_
        
        # Анализ кластеров
        cluster_stats = self._analyze_clusters(
            labels, centers, pore_properties, microns_per_pixel
        )
        
        return labels, centers, cluster_stats
    
    def calculate_pore_orientation(
        self, 
        pore_properties: List, 
        microns_per_pixel: float
    ) -> Optional[Dict[str, Any]]:
        """
        Анализирует ориентацию пор и выявляет предпочтительные направления.
        
        Args:
            pore_properties: Список свойств пор
            microns_per_pixel: Соотношение микрометров к пикселям
            
        Returns:
            Статистика ориентации пор
        """
        min_aspect_ratio = self.orientation_config['MIN_ASPECT_RATIO']
        strength_threshold = self.orientation_config['ORIENTATION_STRENGTH_THRESHOLD']
        
        # Фильтрация пор с вытянутой формой
        valid_props = self._filter_elongated_pores(pore_properties, min_aspect_ratio)
        
        if not valid_props:
            return None
        
        # Извлечение и обработка данных
        orientation_data = self._extract_orientation_data(valid_props, microns_per_pixel)
        
        # Статистический анализ
        return self._analyze_orientation_statistics(orientation_data, strength_threshold)
    
    def calculate_pore_shapes(
        self, 
        pore_properties: List, 
        microns_per_pixel: float
    ) -> pd.DataFrame:
        """
        Анализирует форму пор и классифицирует их.
        
        Args:
            pore_properties: Список свойств пор
            microns_per_pixel: Соотношение микрометров к пикселям
            
        Returns:
            DataFrame с характеристиками формы пор
        """
        if not pore_properties:
            return pd.DataFrame()
        
        # Извлечение базовых свойств
        shape_data = self._extract_shape_properties(pore_properties, microns_per_pixel)
        
        # Вычисление метрик формы
        shape_metrics = self._calculate_shape_metrics(shape_data)
        
        # Классификация типов форм
        shape_types = self._classify_shape_types(shape_metrics)
        
        # Создание итогового DataFrame
        return self._create_shape_dataframe(shape_data, shape_metrics, shape_types)
    
    # Вспомогательные методы
    def _create_size_bins(self, diameters: np.ndarray, bin_count: int) -> Tuple[np.ndarray, List[str]]:
        """Создает интервалы для размеров пор"""
        min_diam, max_diam = diameters.min(), diameters.max()
        bin_edges = np.linspace(min_diam, max_diam, bin_count)
        bin_labels = [f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}" for i in range(len(bin_edges)-1)]
        return bin_edges, bin_labels
    
    def _collect_size_statistics(
        self, 
        pore_bins: np.ndarray, 
        bin_labels: List[str],
        areas_microns: np.ndarray, 
        volumes_microns: np.ndarray
    ) -> pd.DataFrame:
        """Собирает статистику по размерным интервалам"""
        df_data = []
        for bin_idx in range(len(bin_labels)):
            mask = pore_bins == bin_idx
            if np.any(mask):
                count = np.sum(mask)
                total_area = np.sum(areas_microns[mask])
                total_volume = np.sum(volumes_microns[mask])
                
                df_data.append({
                    'Интервал диаметров (мкм)': bin_labels[bin_idx],
                    'Количество пор': count,
                    'Общая площадь (мкм²)': total_area,
                    'Общий объем (мкм³)': total_volume,
                    'Средняя площадь поры (мкм²)': total_area / count,
                    'Средний объем поры (мкм³)': total_volume / count
                })
        
        return pd.DataFrame(df_data)
    
    def _analyze_clusters(
        self, 
        labels: np.ndarray, 
        centers: np.ndarray,
        pore_properties: List, 
        microns_per_pixel: float
    ) -> Dict:
        """Анализирует статистику кластеров"""
        unique_labels = np.unique(labels)
        cluster_stats = {}
        
        # Предварительная обработка данных
        areas_pixels = np.array([prop.area for prop in pore_properties])
        areas_microns = areas_pixels * (microns_per_pixel ** 2)
        diameters_microns = vectorized_equivalent_diameter(areas_pixels) * microns_per_pixel
        
        for label in unique_labels:
            if label != -1:  # Исключение шума
                mask = labels == label
                cluster_centers = centers[mask]
                
                # Геометрия кластера
                centroid = np.mean(cluster_centers, axis=0)
                distances = np.linalg.norm(cluster_centers - centroid, axis=1)
                radius = np.max(distances) if len(distances) > 0 else 0
                
                cluster_stats[label] = {
                    'count': np.sum(mask),
                    'total_area_microns': np.sum(areas_microns[mask]),
                    'mean_area_microns': np.mean(areas_microns[mask]),
                    'mean_diameter_microns': np.mean(diameters_microns[mask]),
                    'density': np.sum(mask) / (np.pi * (radius * microns_per_pixel)**2) if radius > 0 else 0,
                    'centroid': centroid,
                    'radius': radius
                }
        
        return cluster_stats
    
    def _filter_elongated_pores(self, pore_properties: List, min_aspect_ratio: float) -> List:
        """Фильтрует поры с вытянутой формой"""
        valid_props = []
        for prop in pore_properties:
            if (hasattr(prop, 'major_axis_length') and hasattr(prop, 'minor_axis_length') and
                prop.minor_axis_length > 0 and 
                prop.major_axis_length > min_aspect_ratio * prop.minor_axis_length):
                valid_props.append(prop)
        return valid_props
    
    def _extract_orientation_data(self, valid_props: List, microns_per_pixel: float) -> Dict:
        """Извлекает данные ориентации"""
        orientations = np.array([prop.orientation for prop in valid_props])
        major_axes = np.array([prop.major_axis_length for prop in valid_props])
        minor_axes = np.array([prop.minor_axis_length for prop in valid_props])
        areas = np.array([prop.area for prop in valid_props])
        
        return {
            'orientations_deg': (np.degrees(orientations) + 90) % 180,
            'major_axes_microns': major_axes * microns_per_pixel,
            'minor_axes_microns': minor_axes * microns_per_pixel,
            'aspect_ratios': safe_divide(major_axes, minor_axes, 1.0),
            'areas_microns': areas * (microns_per_pixel ** 2)
        }
    
    def _analyze_orientation_statistics(self, data: Dict, strength_threshold: float) -> Dict:
        """Анализирует статистику ориентации"""
        orientations_deg = data['orientations_deg']
        orientations_rad = np.radians(orientations_deg)
        
        # Круговая статистика
        mean_orientation = circmean(orientations_rad)
        std_orientation = circstd(orientations_rad)
        
        # Сила направленности
        sin_sum = np.sum(np.sin(2 * orientations_rad))
        cos_sum = np.sum(np.cos(2 * orientations_rad))
        R = np.sqrt(sin_sum**2 + cos_sum**2) / len(orientations_rad)
        
        # Формирование свойств пор
        filtered_properties = [
            {
                'orientation': orientations_deg[i],
                'major_axis': data['major_axes_microns'][i],
                'minor_axis': data['minor_axes_microns'][i],
                'aspect_ratio': data['aspect_ratios'][i],
                'area': data['areas_microns'][i]
            }
            for i in range(len(orientations_deg))
        ]
        
        return {
            'mean_orientation': np.degrees(mean_orientation) % 180,
            'std_orientation': np.degrees(std_orientation),
            'orientation_strength': R,
            'has_preferred_direction': R > strength_threshold,
            'orientations': orientations_deg.tolist(),
            'filtered_properties': filtered_properties
        }
    
    def _extract_shape_properties(self, pore_properties: List, microns_per_pixel: float) -> Dict:
        """Извлекает базовые свойства формы"""
        return {
            'areas': np.array([prop.area for prop in pore_properties]) * (microns_per_pixel ** 2),
            'perimeters': np.array([prop.perimeter for prop in pore_properties]) * microns_per_pixel,
            'solidities': np.array([getattr(prop, 'solidity', 1.0) for prop in pore_properties]),
            'orientations': np.array([getattr(prop, 'orientation', 0) for prop in pore_properties]),
            'centroids_x': np.array([prop.centroid[1] for prop in pore_properties]) * microns_per_pixel,
            'centroids_y': np.array([prop.centroid[0] for prop in pore_properties]) * microns_per_pixel,
            'properties': pore_properties
        }
    
    def _calculate_shape_metrics(self, shape_data: Dict) -> Dict:
        """Вычисляет метрики формы"""
        areas = shape_data['areas']
        perimeters = shape_data['perimeters']
        
        # Основные метрики
        circularities = safe_divide(4 * np.pi * areas, perimeters ** 2, 0.0)
        equiv_diameters = 2 * np.sqrt(areas / np.pi)
        equiv_radii = equiv_diameters / 2
        compactnesses = safe_divide(areas, np.pi * equiv_radii ** 2, 1.0)
        
        # Эллиптичность и соотношение сторон
        ellipticities, aspect_ratios = self._calculate_ellipticity(shape_data['properties'])
        
        return {
            'circularities': circularities,
            'ellipticities': ellipticities,
            'aspect_ratios': aspect_ratios,
            'compactnesses': compactnesses
        }
    
    def _calculate_ellipticity(self, pore_properties: List) -> Tuple[np.ndarray, np.ndarray]:
        """Вычисляет эллиптичность пор"""
        ellipticities = np.ones(len(pore_properties))
        
        for i, prop in enumerate(pore_properties):
            if hasattr(prop, 'inertia_tensor_eigvals'):
                eigvals = prop.inertia_tensor_eigvals
                if len(eigvals) >= 2 and eigvals[1] > 0:
                    ellipticities[i] = np.sqrt(eigvals[0] / eigvals[1])
            elif hasattr(prop, 'major_axis_length') and hasattr(prop, 'minor_axis_length'):
                major_axis = prop.major_axis_length
                minor_axis = prop.minor_axis_length
                if minor_axis > 0:
                    ellipticities[i] = major_axis / minor_axis
        
        return ellipticities, ellipticities  # aspect_ratios = ellipticities
    
    def _classify_shape_types(self, metrics: Dict) -> np.ndarray:
        """Классифицирует типы форм пор"""
        shape_types = np.full(len(metrics['circularities']), "Неопределенная", dtype=object)
        
        # Получение пороговых значений
        circular_thresh = self.shape_config['CIRCULAR_THRESHOLD']
        oval_thresh = self.shape_config['OVAL_THRESHOLD']
        elongated_thresh = self.shape_config['ELONGATED_THRESHOLD']
        linear_thresh = self.shape_config['LINEAR_THRESHOLD']
        
        # Применение условий классификации
        circularities = metrics['circularities']
        ellipticities = metrics['ellipticities']
        
        # Маски для разных типов форм
        round_mask = circularities > circular_thresh
        oval_mask = (circularities >= oval_thresh) & (circularities <= circular_thresh) & (ellipticities < 1.5)
        elongated_mask = (ellipticities >= 1.5) & (ellipticities < 3)
        linear_mask = ellipticities >= 3
        
        shape_types[round_mask] = "Круглая"
        shape_types[oval_mask] = "Овальная"
        shape_types[elongated_mask] = "Удлиненная"
        shape_types[linear_mask] = "Линейная"
        shape_types[metrics['compactnesses'] < 0.8] = "Неправильная"
        
        return shape_types
    
    def _create_shape_dataframe(
        self, 
        shape_data: Dict, 
        metrics: Dict, 
        shape_types: np.ndarray
    ) -> pd.DataFrame:
        """Создает итоговый DataFrame с характеристиками формы"""
        return pd.DataFrame({
            'ID': np.arange(1, len(shape_data['properties']) + 1),
            'Площадь (мкм²)': shape_data['areas'],
            'Периметр (мкм)': shape_data['perimeters'],
            'Круговой фактор': metrics['circularities'],
            'Эллиптичность': metrics['ellipticities'],
            'Соотношение сторон': metrics['aspect_ratios'],
            'Компактность': metrics['compactnesses'],
            'Солидность': shape_data['solidities'],
            'Тип формы': shape_types,
            'Центроид X': shape_data['centroids_x'],
            'Центроид Y': shape_data['centroids_y'],
            'Ориентация': shape_data['orientations']
        })


# Глобальный экземпляр калькулятора для обратной совместимости
_calculator = PorosityCalculator()

# Функции обратной совместимости
def calculate_pore_size_distribution(pore_properties, pore_diameters_microns, microns_per_pixel):
    """Функция обратной совместимости для расчета распределения размеров пор"""
    return _calculator.calculate_pore_size_distribution(pore_properties, pore_diameters_microns, microns_per_pixel)

def calculate_interpore_distances(pore_properties, microns_per_pixel):
    """Функция обратной совместимости для расчета межпоровых расстояний"""
    return _calculator.calculate_interpore_distances(pore_properties, microns_per_pixel)

def calculate_pore_clusters(pore_properties, microns_per_pixel, min_samples=3, eps_microns=10):
    """Функция обратной совместимости для расчета кластеров пор"""
    return _calculator.calculate_pore_clusters(pore_properties, microns_per_pixel, min_samples, eps_microns)

def calculate_pore_orientation(pore_properties, microns_per_pixel):
    """Функция обратной совместимости для расчета ориентации пор"""
    return _calculator.calculate_pore_orientation(pore_properties, microns_per_pixel)

def calculate_pore_shapes(pore_properties, microns_per_pixel):
    """Функция обратной совместимости для расчета форм пор"""
    return _calculator.calculate_pore_shapes(pore_properties, microns_per_pixel) 