import cv2
import os
import numpy as np

from django.conf import settings

from skimage import io, color, morphology, measure
from skimage.feature import peak_local_max
from skimage.segmentation import watershed
from skimage.filters.rank import entropy
from skimage.morphology import disk

from scipy import ndimage as ndi

from sklearn.cluster import KMeans

from src.modules.porosity_analysis.scripts.utils import batch_process_properties
from src.modules.porosity_analysis.scripts.preprocessing import detect_and_exclude_anomalies
from src.modules.porosity_analysis.scripts.ml_line_detector import MLLineDetector, create_sample_training_data

def advanced_porosity_analysis(image_path, pixels_per_micron, scale_region, save_directory=None):
    """
    Продвинутый анализ пористости с использованием комбинации методов 
    с учетом масштаба и исключением области измерительной линейки, линий и аномалий
    
    Args:
        image_path (str): Путь к изображению
        pixels_per_micron (float): Соотношение пикселей к микрометрам
        scale_region (tuple): Координаты области линейки для исключения из анализа
        save_directory (str, optional): Директория для сохранения модели ML
        
    Returns:
        dict: Результаты анализа
    """
    # Коэффициент пересчета пикселей в микрометры
    microns_per_pixel = 1.0 / pixels_per_micron
    
    # Загрузка изображения
    image = io.imread(image_path)
    
    # Оптимизированное преобразование в оттенки серого
    if len(image.shape) == 3 and image.shape[2] == 3:
        gray = color.rgb2gray(image)
        if gray.max() <= 1.0:
            gray = (gray * 255).astype(np.uint8)
    else:
        gray = image.astype(np.uint8)
    
    # Создание базовой маски для исключения области линейки
    scale_exclude_mask = np.ones_like(gray, dtype=bool)
    sx, sy, sw, sh = scale_region
    scale_exclude_mask[sy:sy+sh, sx:sx+sw] = False
    
    # Обнаружение и исключение линий с помощью ML детектора
    print("Обнаружение линий с помощью ML детектора...")
    
    # Получаем директорию с данными анализа для поиска модели
    if save_directory is None:
        save_directory = os.path.dirname(image_path)
    
    # Используем глобальную папку для обученных моделей
    trained_models_dir = os.path.join(settings.BASE_DIR, "trained_models")
    os.makedirs(trained_models_dir, exist_ok=True)
    
    model_path = os.path.join(trained_models_dir, "ml_line_detector.pkl")
    
    try:
        # Пытаемся загрузить существующую модель
        if os.path.exists(model_path):
            ml_detector = MLLineDetector(model_path)
            print(f"  - Загружена предобученная модель: {model_path}")
        else:
            # Создаем и обучаем новую модель на текущем изображении
            print("  - Создание и обучение новой ML модели...")
            ml_detector = create_sample_training_data(
                image_paths=[image_path], 
                save_path=model_path
            )
            print(f"  - Модель сохранена в: {model_path}")
        
        # Детекция линий с оптимизированными параметрами
        lines_exclude_mask = ml_detector.detect_and_exclude_lines(
            gray, 
            dilation_size=5,
            confidence_threshold=0.4  # Немного снижен для лучшего захвата линий
        )
        print(f"  - ML детектор успешно применен")
        
    except Exception as e:
        print(f"  - Ошибка ML детектора: {e}")
    
    # Обнаружение и исключение аномалий
    print("Обнаружение аномалий для исключения...")
    anomalies_exclude_mask = detect_and_exclude_anomalies(gray)
    
    # Комбинирование всех масок исключения
    exclude_mask = scale_exclude_mask & lines_exclude_mask & anomalies_exclude_mask
    
    print(f"Исключено из анализа:")
    print(f"  - Область шкалы: {np.sum(~scale_exclude_mask)} пикселей")
    print(f"  - Области линий: {np.sum(~lines_exclude_mask)} пикселей")
    print(f"  - Аномальные области: {np.sum(~anomalies_exclude_mask)} пикселей")
    print(f"  - Общая исключенная область: {np.sum(~exclude_mask)} пикселей ({(np.sum(~exclude_mask)/gray.size)*100:.2f}%)")
    
    # 1. Улучшение контраста изображения
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 2. Шумоподавление с сохранением краев
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    
    # 3. Извлечение признаков для улучшения сегментации
    # 3.2 Локальная вариация (текстурный признак)
    texture = entropy(denoised, disk(3))
    
    # 4. Кластеризация для сегментации
    # Подготовка признаков (пиксели + текстура) - избегаем flatten для экономии памяти
    h, w = denoised.shape
    features = np.column_stack([
        denoised.ravel(),
        texture.ravel()
    ])
    
    # Применение K-means для сегментации на K кластеров
    K = 3  # Обычно достаточно 3 кластера: фон, материал, поры
    kmeans = KMeans(n_clusters=K, random_state=42, n_init=10)
    labels = kmeans.fit_predict(features)
    segmented = labels.reshape(h, w)
    
    # 5. Определение кластера, соответствующего порам
    # Поры обычно самые темные области - векторизованно
    cluster_means = np.full(K, np.inf)
    for i in range(K):
        mask = (segmented == i) & exclude_mask
        if np.any(mask):
            cluster_means[i] = np.mean(denoised[mask])
    
    pore_cluster = np.argmin(cluster_means)
    
    # Бинарная маска пор с применением маски исключения
    pore_mask = (segmented == pore_cluster) & exclude_mask
    
    # 6. Постобработка для удаления шума и улучшения сегментации
    # Морфологическое открытие для удаления мелких шумов
    cleaned_mask = morphology.binary_opening(pore_mask, morphology.disk(3))
    
    # Удаление слишком маленьких объектов
    cleaned_mask = morphology.remove_small_objects(cleaned_mask, min_size=5)
    
    # 7. Разделение слипшихся пор с помощью водораздела
    # Расчет расстояния от каждой точки поры до фона
    distance = ndi.distance_transform_edt(cleaned_mask)
    
    # Поиск локальных максимумов на карте расстояний
    local_maxi = peak_local_max(distance, footprint=np.ones((3, 3)), labels=cleaned_mask)
    markers = np.zeros_like(distance, dtype=bool)
    markers[tuple(local_maxi.T)] = True
    markers = ndi.label(markers)[0]
    
    # Применение алгоритма водораздела для сегментации слипшихся пор
    watershed_result = watershed(-distance, markers, mask=cleaned_mask)
    
    # 8. Маркировка и подсчет статистики
    labeled_pores, num_pores = measure.label(watershed_result, return_num=True)
    pore_properties = measure.regionprops(labeled_pores)
    
    # Векторизованные расчеты с использованием batch_process_properties
    if pore_properties:
        batch_data = batch_process_properties(pore_properties, microns_per_pixel)
        pore_sizes_pixels = batch_data['areas_pixels'].tolist()
        pore_sizes_microns = batch_data['areas_microns'].tolist()
        pore_diameters_microns = batch_data['diameters_microns'].tolist()
        
        # Статистика по размерам пор
        mean_pore_size_microns = np.mean(batch_data['areas_microns'])
        median_pore_size_microns = np.median(batch_data['areas_microns'])
        mean_pore_diameter_microns = np.mean(batch_data['diameters_microns'])
        median_pore_diameter_microns = np.median(batch_data['diameters_microns'])
        mean_pore_size_pixels = np.mean(batch_data['areas_pixels'])
    else:
        pore_sizes_pixels = []
        pore_sizes_microns = []
        pore_diameters_microns = []
        mean_pore_size_microns = 0
        median_pore_size_microns = 0
        mean_pore_size_pixels = 0
        mean_pore_diameter_microns = 0
        median_pore_diameter_microns = 0
    
    # Расчет пористости
    total_area = np.sum(exclude_mask)
    pore_area = np.sum(cleaned_mask)
    porosity = (pore_area / total_area) * 100
    
    # Расчет дополнительных метрик
    if pore_sizes_microns:
        max_pore_size_microns = max(pore_sizes_microns)
        min_pore_size_microns = min(pore_sizes_microns)
        pore_density = num_pores / (total_area * microns_per_pixel * microns_per_pixel)  # пор/мкм²
    else:
        max_pore_size_microns = 0
        min_pore_size_microns = 0
        pore_density = 0
    
    # Расчет среднего межпорового расстояния
    if len(pore_properties) >= 2:
        from .calculations import calculate_interpore_distances
        interpore_distances, _ = calculate_interpore_distances(pore_properties, microns_per_pixel)
        average_interpore_distance = np.mean(interpore_distances) if interpore_distances is not None else 0
    else:
        average_interpore_distance = 0
    
    # Формирование результатов
    results = {
        'porosity_percentage': porosity,
        'relative_pore_area': porosity,  # это уже вычислено как пористость
        'number_of_pores': num_pores,
        'mean_pore_size_pixels': mean_pore_size_pixels,
        'mean_pore_size_microns': mean_pore_size_microns,
        'median_pore_size_microns': median_pore_size_microns,
        'max_pore_size_microns': max_pore_size_microns,
        'min_pore_size_microns': min_pore_size_microns,
        'mean_pore_diameter_microns': mean_pore_diameter_microns,
        'median_pore_diameter_microns': median_pore_diameter_microns,
        'pore_density': pore_density,
        'average_interpore_distance': average_interpore_distance,
        'pore_sizes_pixels': pore_sizes_pixels,
        'pore_sizes_microns': pore_sizes_microns,
        'pore_diameters_microns': pore_diameters_microns,
        'labeled_pores': labeled_pores,
        'binary_mask': cleaned_mask,
        'scale_factor': microns_per_pixel,
        'scale_region': scale_region,
        'pore_properties': pore_properties,
        # Данные для визуализации
        'gray': gray,
        'enhanced': enhanced,
        'texture': texture,
        'segmented': segmented,
        'exclude_mask': exclude_mask,
        # Новые маски исключения
        'lines_exclude_mask': lines_exclude_mask,
        'anomalies_exclude_mask': anomalies_exclude_mask,
        'scale_exclude_mask': scale_exclude_mask
    }
    
    return results 