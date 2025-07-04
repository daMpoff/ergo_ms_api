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

# Настройки файлов
FILES = {
    'IMAGE_WITH_SCALE_FILENAME': 'image_with_scale_bar.png',
    'SCALE_BAR_FILENAME': 'scale_bar.png',
    'CONTRAST_STAGES_FILENAME': 'figure1_contrast.png',
    'EXCLUDED_AREAS_FILENAME': 'figure2_excluded_areas.png',
    'TEXTURE_CLUSTERS_FILENAME': 'figure3_texture_clusters.png',
    'MASK_RESULT_FILENAME': 'figure4_mask_result.png',
    'OVERLAY_FILENAME': 'figure5_overlay.png',
    'PORE_SIZE_DISTRIBUTION_FILENAME': 'pore_size_distribution.png',
    'INTERPORE_DISTANCES_FILENAME': 'interpore_distances.png',
    'PORE_ORIENTATION_ROSE_FILENAME': 'pore_orientation_rose.png',
    'PORE_ORIENTATION_HISTOGRAM_FILENAME': 'pore_orientation_histogram.png',
    'PORE_SHAPES_ANALYSIS_FILENAME': 'pore_shapes_analysis.png',
    'CIRCULARITY_DISTRIBUTION_FILENAME': 'circularity_distribution.png',
    'ELLIPTICITY_VS_AREA_FILENAME': 'ellipticity_vs_area.png',
}

# Сообщения для логирования
MESSAGES = {
    'SCALE_DETECTED': '✓ Масштабная линейка обнаружена',
    'ANOMALIES_DETECTION': "Обнаружение аномалий для исключения...",
    'LINES_DETECTION': "Обнаружение линий с помощью ML детектора...",
    'ML_MODEL_LOADED': "Загружена предобученная модель:",
    'ML_MODEL_CREATED': "Создание и обучение новой ML модели...",
    'ML_MODEL_APPLIED': "ML детектор успешно применен",
    'ML_MODEL_ERROR': "Ошибка ML детектора:",
    'CALCULATIONS_START': '📊 Выполняются дополнительные расчеты...',
    'VISUALIZATIONS_START': '🎨 Создание визуализаций...',
    'VISUALIZATIONS_COMPLETE': '✓ Все визуализации созданы',
}

# Параметры анализа
ANALYSIS_PARAMS = {
    'MIN_PORE_SIZE': 10,  # минимальный размер поры в пикселях
    'MAX_PORE_SIZE': 1000,  # максимальный размер поры в пикселях
    'CONTRAST_THRESHOLD': 0.5,  # порог контраста
    'TEXTURE_SENSITIVITY': 0.3,  # чувствительность текстуры
    'SCALE_DETECTION_CONFIDENCE': 0.8,  # уверенность в детекции шкалы
}

# Настройки визуализации
VISUALIZATION_PARAMS = {
    'FIGURE_SIZE': (12, 8),
    'DPI': 300,
    'COLOR_MAP': 'viridis',
    'FONT_SIZE': 12,
    'LINE_WIDTH': 2,
}

# Настройки экспорта
EXPORT_PARAMS = {
    'IMAGE_FORMAT': 'png',
    'COMPRESSION': 95,
    'METADATA': True,
}

# Ограничения
LIMITS = {
    'MAX_IMAGE_SIZE': 50 * 1024 * 1024,  # 50 МБ
    'MAX_IMAGE_DIMENSION': 10000,  # максимальный размер изображения
    'MIN_SCALE_VALUE': 0.1,  # минимальное значение шкалы
    'MAX_SCALE_VALUE': 10000,  # максимальное значение шкалы
    'MAX_BATCH_FILES': 20,  # максимальное количество файлов в пакете
}

# Поддерживаемые форматы
SUPPORTED_FORMATS = [
    'image/jpeg',
    'image/png', 
    'image/bmp',
    'image/tiff',
    'image/tif'
]

# Расширения файлов
SUPPORTED_EXTENSIONS = [
    '.jpg',
    '.jpeg',
    '.png',
    '.bmp',
    '.tiff',
    '.tif'
] 