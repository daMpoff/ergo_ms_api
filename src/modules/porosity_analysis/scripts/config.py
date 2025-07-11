"""
Конфигурационные константы для анализа пористости
"""

# Параметры обработки изображений
IMAGE_PROCESSING = {
    'CLAHE_CLIP_LIMIT': 2.0,
    'CLAHE_TILE_GRID_SIZE': (8, 8),
    'BILATERAL_FILTER_D': 9,
    'BILATERAL_SIGMA_COLOR': 75,
    'BILATERAL_SIGMA_SPACE': 75,
    'GAUSSIAN_BLUR_KERNEL': (3, 3),
    'ADAPTIVE_THRESHOLD_BLOCK_SIZE': 9,
    'ADAPTIVE_THRESHOLD_C': 2,
}

# Параметры морфологических операций
MORPHOLOGY = {
    'TEXTURE_ENTROPY_DISK_SIZE': 3,
    'OPENING_DISK_SIZE': 3,
    'MIN_OBJECT_SIZE': 5,
    'WATERSHED_FOOTPRINT_SIZE': (3, 3),
    'EROSION_KERNEL_SIZE': (2, 2),
    'DILATION_KERNEL_SIZE': (3, 3),
}

# Параметры кластеризации
CLUSTERING = {
    'KMEANS_CLUSTERS': 3,
    'KMEANS_RANDOM_STATE': 42,
    'KMEANS_N_INIT': 10,
    'DBSCAN_MIN_SAMPLES': 3,
    'DBSCAN_EPS_MICRONS': 10,
}

# Параметры детекции шкалы
SCALE_DETECTION = {
    'ROI_FRACTION': 0.75,  # Поиск в нижней правой четверти
    'BINARY_THRESHOLD': 200,
    'MIN_WIDTH_FRACTION': 0.05,  # Минимальная ширина линейки относительно изображения
    'ASPECT_RATIO_THRESHOLD': 5,  # Соотношение ширины к высоте для линейки
    'SCALE_REGION_PADDING': 10,
}

# Параметры детекции аномалий
ANOMALY_DETECTION = {
    'THRESHOLD_FACTOR': 2.0,
    'SCALE_FACTOR': 0.3,  # Коэффициент уменьшения для ускорения
    'BLUR_KERNEL_SIZE': (3, 3),
    'MORPHOLOGY_KERNEL_SIZE': (2, 2),
}

# Параметры ML детектора линий
ML_LINE_DETECTOR = {
    'MIN_OBJECT_AREA': 10,
    'DILATION_SIZE': 5,
    'CONFIDENCE_THRESHOLD': 0.4,
    'ASPECT_RATIO_THRESHOLD': 3.5,
    'ECCENTRICITY_THRESHOLD': 0.85,
    'MIN_LINE_AREA': 20,
}

# Параметры анализа ориентации
ORIENTATION_ANALYSIS = {
    'MIN_ASPECT_RATIO': 1.5,  # Минимальное соотношение осей для анализа ориентации
    'ORIENTATION_STRENGTH_THRESHOLD': 0.3,  # Порог для определения предпочтительного направления
    'HISTOGRAM_BINS': 18,
}

# Параметры анализа форм
SHAPE_ANALYSIS = {
    'CIRCULAR_THRESHOLD': 0.8,  # Порог кругового фактора для "круглых" пор
    'OVAL_THRESHOLD': 0.6,
    'ELONGATED_THRESHOLD': 0.4,
    'LINEAR_THRESHOLD': 0.2,
}

# Параметры размеров
SIZE_ANALYSIS = {
    'SIZE_DISTRIBUTION_BINS': 6,  # Количество интервалов для распределения размеров
}

# Параметры визуализации
VISUALIZATION = {
    'DPI': 300,
    'FIGURE_SIZE_STANDARD': (12, 6),
    'FIGURE_SIZE_LARGE': (12, 12),
    'FIGURE_SIZE_ANALYSIS': (15, 7),
    'ROSE_DIAGRAM_BINS': 36,
    'HISTOGRAM_ALPHA': 0.7,
}

# Пути к файлам
FILES = {
    'ML_MODEL_FILENAME': 'ml_line_detector.pkl',
    'SCALE_BAR_FILENAME': 'scale_bar.png',
    'IMAGE_WITH_SCALE_FILENAME': 'image_with_scale_bar.png',
}

# Сообщения для логирования
MESSAGES = {
    'SCALE_DETECTED': "Определен масштаб:",
    'ANOMALIES_DETECTION': "Обнаружение аномалий для исключения...",
    'LINES_DETECTION': "Обнаружение линий с помощью ML детектора...",
    'ML_MODEL_LOADED': "Загружена предобученная модель:",
    'ML_MODEL_CREATED': "Создание и обучение новой ML модели...",
    'ML_MODEL_APPLIED': "ML детектор успешно применен",
    'ML_MODEL_ERROR': "Ошибка ML детектора:",
    'CALCULATIONS_START': "Выполнение дополнительных расчетов...",
    'VISUALIZATIONS_START': "Создание визуализаций...",
    'VISUALIZATIONS_COMPLETE': "Визуализации созданы и сохранены.",
}

class AnalysisConfig:
    """Класс конфигурации для анализа пористости"""
    
    def __init__(self, input_image_path, output_directory, scale_value, pixels_per_micron=None):
        self.input_image_path = input_image_path
        self.output_directory = output_directory
        self.scale_value = scale_value
        self.pixels_per_micron = pixels_per_micron 