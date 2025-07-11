"""
Модуль предобработки изображений для анализа пористости
"""
import os
from typing import Tuple

import cv2
import numpy as np

from skimage.morphology import disk, dilation

from scipy.ndimage import label

from src.modules.porosity_analysis.scripts.config import ANOMALY_DETECTION, SCALE_DETECTION, FILES, MESSAGES

class ImagePreprocessor:
    """Класс для предобработки изображений микроскопии"""
    
    def __init__(self):
        self.config = ANOMALY_DETECTION
        self.scale_config = SCALE_DETECTION
    
    def detect_and_exclude_anomalies(
        self, 
        image: np.ndarray, 
        threshold_factor: float = None,
        scale_factor: float = None
    ) -> np.ndarray:
        """
        Обнаруживает и исключает аномальные области (крупные дефекты) на изображении.
        
        Args:
            image: Входное изображение в оттенках серого
            threshold_factor: Коэффициент для определения аномальных областей
            scale_factor: Коэффициент масштабирования для ускорения
            
        Returns:
            Маска для исключения аномалий (True там, где аномалий нет)
        """
        if threshold_factor is None:
            threshold_factor = self.config['THRESHOLD_FACTOR']
        if scale_factor is None:
            scale_factor = self.config['SCALE_FACTOR']
            
        original_shape = image.shape
        
        # Уменьшаем изображение для быстрого анализа
        resized_image = self._resize_image_for_analysis(image, scale_factor)
        
        # Предобработка
        preprocessed = self._preprocess_for_anomaly_detection(resized_image)
        
        # Бинаризация
        binary = self._adaptive_threshold(preprocessed)
        
        # Морфологическое открытие
        opened = self._morphological_opening(binary)
        
        # Поиск и фильтрация аномалий
        anomaly_mask_small = self._find_and_filter_anomalies(
            opened, threshold_factor, resized_image.shape
        )
        
        # Масштабирование обратно к оригинальному размеру
        return self._resize_mask_to_original(anomaly_mask_small, original_shape, scale_factor)
    
    def _resize_image_for_analysis(self, image: np.ndarray, scale_factor: float) -> np.ndarray:
        """Изменяет размер изображения для анализа"""
        if scale_factor >= 1.0:
            return image
            
        new_height = int(image.shape[0] * scale_factor)
        new_width = int(image.shape[1] * scale_factor)
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    def _preprocess_for_anomaly_detection(self, image: np.ndarray) -> np.ndarray:
        """Предобработка изображения для детекции аномалий"""
        kernel_size = self.config['BLUR_KERNEL_SIZE']
        return cv2.GaussianBlur(image.astype(np.uint8), kernel_size, 0)
    
    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Применяет адаптивную бинаризацию"""
        return cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 9, 2
        )
    
    def _morphological_opening(self, binary: np.ndarray) -> np.ndarray:
        """Применяет морфологическое открытие"""
        kernel_size = self.config['MORPHOLOGY_KERNEL_SIZE']
        kernel = np.ones(kernel_size, np.uint8)
        return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    def _find_and_filter_anomalies(
        self, 
        opened: np.ndarray, 
        threshold_factor: float,
        image_shape: Tuple[int, int]
    ) -> np.ndarray:
        """Находит и фильтрует аномальные области"""
        labeled, num_components = label(opened)
        
        if num_components == 0:
            return np.ones(image_shape, dtype=bool)
        
        # Векторизованное вычисление площадей
        unique_labels, counts = np.unique(labeled[labeled > 0], return_counts=True)
        areas = counts
        
        if len(areas) == 0:
            return np.ones(image_shape, dtype=bool)
        
        # Определение порога для аномалий
        mean_area = np.mean(areas)
        std_area = np.std(areas)
        area_threshold = mean_area + threshold_factor * std_area
        
        # Нахождение аномальных компонентов
        anomalous_labels = unique_labels[areas > area_threshold]
        
        if len(anomalous_labels) == 0:
            return np.ones(image_shape, dtype=bool)
        
        # Создание маски аномалий
        anomaly_mask = np.ones(image_shape, dtype=bool)
        for label_id in anomalous_labels:
            anomaly_mask[labeled == label_id] = False
        
        # Расширение аномальных областей
        if not np.all(anomaly_mask):
            inverted_mask = ~anomaly_mask
            if np.any(inverted_mask):
                dilated = dilation(inverted_mask, np.ones((3, 3), dtype=bool))
                anomaly_mask = ~dilated
        
        return anomaly_mask
    
    def _resize_mask_to_original(
        self, 
        mask: np.ndarray, 
        original_shape: Tuple[int, int],
        scale_factor: float
    ) -> np.ndarray:
        """Изменяет размер маски обратно к оригинальному"""
        if scale_factor >= 1.0:
            return mask
            
        return cv2.resize(
            mask.astype(np.uint8), 
            (original_shape[1], original_shape[0]), 
            interpolation=cv2.INTER_NEAREST
        ).astype(bool)


class ScaleDetector:
    """Класс для обнаружения измерительной шкалы на изображениях микроскопа"""
    
    def __init__(self):
        self.config = SCALE_DETECTION
    
    def detect_scale_bar(
        self, 
        image_path: str, 
        scale_value: float, 
        save_directory: str,
        scale_region_padding: int = None
    ) -> Tuple[float, np.ndarray, Tuple[int, int, int, int]]:
        """
        Обнаруживает измерительную линейку на изображении микроскопа.
        
        Args:
            image_path: Путь к изображению
            scale_value: Значение шкалы в микрометрах
            save_directory: Директория для сохранения результатов
            scale_region_padding: Отступы вокруг области линейки
            
        Returns:
            Кортеж: (соотношение пикселей к микрометрам, результирующее изображение, координаты области)
        """
        if scale_region_padding is None:
            scale_region_padding = self.config['SCALE_REGION_PADDING']
        
        # Загрузка изображения
        img = self._load_image(image_path)
        result_img = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Поиск линейки
        scale_bar = self._find_scale_bar(gray)
        
        # Обработка результатов
        pixels_per_micron, scale_region = self._process_scale_bar_results(
            scale_bar, scale_value, gray.shape, result_img, scale_region_padding
        )
        
        # Сохранение результатов
        self._save_scale_bar_results(gray, scale_bar, save_directory)
        
        return pixels_per_micron, result_img, scale_region
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """Загружает изображение с проверкой"""
        import os
        
        # Проверяем существование файла
        if not os.path.exists(image_path):
            raise ValueError(f"Файл не существует: {image_path}")
        
        # Проверяем размер файла
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            raise ValueError(f"Файл пустой: {image_path}")
        
        # Пробуем загрузить изображение
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Не удалось загрузить изображение (размер файла: {file_size} байт): {image_path}")
        
        # Проверяем, что изображение не пустое
        if img.size == 0:
            raise ValueError(f"Загруженное изображение пустое: {image_path}")
        
        return img
    
    def _find_scale_bar(self, gray: np.ndarray) -> Tuple[int, int, int, int]:
        """Находит линейку на изображении"""
        height, width = gray.shape
        
        # Поиск в нижней правой четверти
        scale_bar = self._search_in_roi(gray, height, width)
        
        # Если не найдено, поиск по всему изображению
        if scale_bar is None:
            scale_bar = self._search_in_full_image(gray, width)
        
        if scale_bar is None:
            raise ValueError("Не удалось обнаружить измерительную линейку")
        
        return scale_bar
    
    def _search_in_roi(self, gray: np.ndarray, height: int, width: int) -> Tuple[int, int, int, int]:
        """Поиск линейки в области интереса (нижняя правая четверть)"""
        roi_fraction = self.config['ROI_FRACTION']
        roi_y = int(height * roi_fraction)
        roi_x = int(width * roi_fraction)
        roi = gray[roi_y:, roi_x:]
        
        candidates = self._find_horizontal_lines(roi, width)
        
        if candidates:
            # Корректировка координат для ROI
            x, y, w, h = max(candidates, key=lambda x: x[2])
            return (x + roi_x, y + roi_y, w, h)
        
        return None
    
    def _search_in_full_image(self, gray: np.ndarray, width: int) -> Tuple[int, int, int, int]:
        """Поиск линейки по всему изображению"""
        candidates = self._find_horizontal_lines(gray, width)
        return max(candidates, key=lambda x: x[2]) if candidates else None
    
    def _find_horizontal_lines(self, image: np.ndarray, image_width: int) -> list:
        """Находит горизонтальные линии (потенциальные линейки)"""
        # Бинаризация для выделения белых элементов
        threshold = self.config['BINARY_THRESHOLD']
        _, binary = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        min_width = image_width * self.config['MIN_WIDTH_FRACTION']
        aspect_ratio_threshold = self.config['ASPECT_RATIO_THRESHOLD']
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if h > 0 and w > aspect_ratio_threshold * h and w > min_width:
                candidates.append((x, y, w, h))
        
        return candidates
    
    def _process_scale_bar_results(
        self, 
        scale_bar: Tuple[int, int, int, int],
        scale_value: float,
        image_shape: Tuple[int, int],
        result_img: np.ndarray,
        padding: int
    ) -> Tuple[float, Tuple[int, int, int, int]]:
        """Обрабатывает результаты обнаружения линейки"""
        x, y, w, h = scale_bar
        height, width = image_shape
        
        # Отметка линейки на изображении
        cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Вычисление соотношения пикселей к микрометрам
        pixels_per_micron = w / scale_value
        
        # Расширенная область линейки для исключения
        scale_region = (
            max(0, x - padding),
            max(0, y - padding),
            min(w + 2 * padding, width - (x - padding)),
            min(h + 2 * padding, height - (y - padding))
        )
        
        # Отметка расширенной области
        sx, sy, sw, sh = scale_region
        cv2.rectangle(result_img, (sx, sy), (sx + sw, sy + sh), (255, 0, 0), 1)
        
        return pixels_per_micron, scale_region
    
    def _save_scale_bar_results(
        self, 
        gray: np.ndarray, 
        scale_bar: Tuple[int, int, int, int],
        save_directory: str
    ) -> None:
        """Сохраняет область линейки"""
        x, y, w, h = scale_bar
        height, width = gray.shape
        
        # Определение области для сохранения
        text_roi_y_min = max(0, y)
        text_roi_y_max = min(height, y + h)
        text_roi_x_min = max(0, x)
        text_roi_x_max = min(width, x + w)
        
        # Извлечение и сохранение области
        text_roi = gray[text_roi_y_min:text_roi_y_max, text_roi_x_min:text_roi_x_max]
        scale_bar_filename = FILES['SCALE_BAR_FILENAME']
        cv2.imwrite(os.path.join(save_directory, scale_bar_filename), text_roi)


# Функции обратной совместимости для сохранения интерфейса
def detect_and_exclude_anomalies(image, threshold_factor=2.0, scale_factor=0.3):
    """Функция обратной совместимости для обнаружения аномалий"""
    preprocessor = ImagePreprocessor()
    return preprocessor.detect_and_exclude_anomalies(image, threshold_factor, scale_factor)


def detect_scale_bar(image_path, scale_value, save_directory, scale_region_padding=10):
    """Функция обратной совместимости для обнаружения шкалы"""
    detector = ScaleDetector()
    return detector.detect_scale_bar(image_path, scale_value, save_directory, scale_region_padding) 