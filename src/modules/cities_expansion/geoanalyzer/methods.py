from collections import defaultdict
from datetime import datetime
import gc
import math
import os
import pickle
import traceback
from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings
from django.core.files import File
from django.db.models import FileField
from django.db.models.fields.files import FieldFile

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

import matplotlib.pyplot as plt
from sklearn.neighbors import KernelDensity
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import ScalarMappable

from src.modules.cities_expansion.models import Task, TaskResult
from src.modules.cities_expansion.models import Group, FileGroup, FileUpload

from src.modules.cities_expansion.geoanalyzer.colors import color_to_name, name_to_color
from src.modules.cities_expansion.geoanalyzer.models import GroupCoords
from src.modules.cities_expansion.geoanalyzer.cities import City, CityObject

from io import BytesIO

from PIL import Image

from sklearn.cluster import KMeans

def parse_coordinate(coord_str):
    # Разделяем координаты по запятой (если их несколько)
    parts = coord_str.split(', ')
    coords = []
    
    for part in parts:
        # Удаляем лишние пробелы и разбиваем на градусы, минуты, секунды
        part = part.strip()
        
        # Извлекаем градусы
        deg_pos = part.find('°')
        degrees = float(part[:deg_pos])
        
        # Извлекаем минуты
        min_pos = part.find("'", deg_pos)  # Используем символ ′ (минуты)
        minutes = float(part[deg_pos + 1 : min_pos])
        
        # Извлекаем секунды
        sec_pos = part.find('"', min_pos)  # Используем символ ″ (секунды)
        seconds = float(part[min_pos + 1 : sec_pos])
        
        # Определяем направление (N, S, E, W)
        direction = part[sec_pos + 1]
        
        # Преобразуем в десятичные градусы
        decimal_degrees = degrees + minutes / 60 + seconds / 3600
        
        # Учитываем направление (S и W дают отрицательные значения)
        if direction in ['S', 'W']:
            decimal_degrees *= -1
        
        coords.append(decimal_degrees)
    
    return tuple(coords)

def save_image_as_file(image: Image.Image, name: str, group: Group) -> FileUpload:
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)

    filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"

    file_obj = File(buffer, name=filename)

    fu = FileUpload()
    fu.filename = filename
    fu.user = group.user
    fu.date = datetime.now()
    fu.file.save(filename, file_obj)
    fu.save()

    fg = FileGroup()
    fg.upload = fu
    fg.group = group
    fg.save()

    return fu

def save_buffer_image_as_file(buffer: BytesIO, name: str, group: Group) -> FileUpload:
    buffer.seek(0)

    filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"

    file_obj = File(buffer, name=filename)

    fu = FileUpload()
    fu.filename = filename
    fu.user = group.user
    fu.date = datetime.now()
    fu.file.save(filename, file_obj)
    fu.save()

    fg = FileGroup()
    fg.upload = fu
    fg.group = group
    fg.save()

    return fu

def save_obj_to_pickle(obj, name: str, group: Group) -> FileUpload:
    buffer = BytesIO()
    pickle.dump(obj, buffer)
    buffer.seek(0)

    filename = f"{name}.pickle"

    file_obj = File(buffer, name=filename)

    fu = FileUpload()
    fu.filename = filename
    fu.user = group.user
    fu.date = datetime.now()
    fu.file.save(filename, file_obj)
    fu.save()

    fg = FileGroup()
    fg.upload = fu
    fg.group = group
    fg.save()

    return fu

def open_image(file: File) -> Image.Image:
    with file.open('rb') as file_image:
        image = Image.open(file)
        image.load()
        return image

def crop_maps(group: Group, city_map: File, buildings_map: File, railways_map: File | None = None) -> list[Image.Image]:
    result = []

    # Фиксированные отступы слева и справа
    left = 63
    right = 63

    with city_map.open('rb') as city_map_file:
        city_map_image = Image.open(city_map_file)

        width, height = city_map_image.size

        top = round(height * 0.06)
        bottom = round(height * 0.04)

        # Область для обрезки (left, top, right, bottom)
        crop_area = (
            left,
            top,
            width - right,
            height - bottom
        )

        city_map_image_cropped = city_map_image.crop(crop_area)

        save_image_as_file(city_map_image_cropped, 'city_map_image_cropped', group)

        result.append(city_map_image_cropped)
    with buildings_map.open('rb') as buildings_map_file:
        buildings_map_image = Image.open(buildings_map_file)
        buildings_map_image_cropped = buildings_map_image.crop(crop_area)

        save_image_as_file(buildings_map_image_cropped, 'buildings_map_image_cropped', group)

        result.append(buildings_map_image_cropped)
    
    if railways_map is not None:
        with railways_map.open('rb') as railways_map_file:
            railways_map_image = Image.open(railways_map_file)
            railways_map_image_cropped = railways_map_image.crop(crop_area)

            save_image_as_file(railways_map_image_cropped, 'railways_map_image_cropped', group)

            result.append(railways_map_image_cropped)
    
    return result

def stack_layers_np(base, *layers):
    """Накладывает изображения друг на друга используя numpy"""
    result = np.array(base.convert('RGBA'))
    for layer in layers:
        layer_arr = np.array(layer.convert('RGBA'))
        alpha = layer_arr[..., 3:] / 255.0
        result = (result * (1 - alpha) + layer_arr * alpha).astype(np.uint8)
    return Image.fromarray(result)

def change_color(image: Image.Image, target_color: tuple[int, int, int], replace_color: tuple[int, int, int], rgb_threshold=16, exact_alpha=255):
    target_color = list(target_color) + [255]
    replace_color = list(replace_color) + [255]

    if (image.mode != 'RGBA'):
        image.putalpha(255)

    arr = np.array(image)
    rgb_mask = np.all(np.abs(arr[..., :3] - target_color[:3]) <= rgb_threshold, axis=-1)
    alpha_mask = (arr[..., 3] == exact_alpha)
    mask = rgb_mask & alpha_mask
    
    output = np.zeros_like(arr)
    output[mask] = replace_color
    
    return Image.fromarray(output)

def make_final_map(group: Group, city_map: Image.Image, buildings_map: Image.Image, railways_map: Image.Image | None = None) -> Image.Image:
    buildings_map_edited = change_color(buildings_map, (0, 0, 0), name_to_color['Building'])

    if railways_map is not None:
        railways_map_edited = change_color(railways_map, (128, 128, 128), name_to_color['Railway'])
        final_map = stack_layers_np(city_map, railways_map_edited, buildings_map_edited)
    else:
        final_map = stack_layers_np(city_map, buildings_map_edited)

    save_image_as_file(final_map, 'final_map', group)
    return final_map

def calculate_scale(image_width: int, image_height: int, 
                   upper_left: tuple, down_right: tuple) -> tuple:
    """
    Вычисляет масштаб изображения (метры/пиксель) по географическим координатам.
    
    Параметры:
        image_width: ширина изображения в пикселях
        image_height: высота изображения в пикселях
        upper_left: (широта, долгота) верхнего левого угла
        down_right: (широта, долгота) нижнего правого угла
    
    Возвращает:
        (x_scale, y_scale) - масштаб по горизонтали и вертикали (метры/пиксель)
    """
    # Средний радиус Земли в метрах
    EARTH_RADIUS = 6_371_000
    
    # Разница координат в радианах
    lat1, lon1 = upper_left
    lat2, lon2 = down_right
    
    # Горизонтальное расстояние (по долготе)
    dlon = math.radians(lon2 - lon1)
    horizontal_dist = dlon * EARTH_RADIUS * math.cos(math.radians((lat1 + lat2) / 2))
    
    # Вертикальное расстояние (по широте)
    dlat = math.radians(lat2 - lat1)
    vertical_dist = dlat * EARTH_RADIUS
    
    # Рассчитываем масштаб
    x_scale = abs(horizontal_dist) / image_width
    y_scale = abs(vertical_dist) / image_height
    
    return (x_scale, y_scale)

def check_color(rgb1: np.ndarray, rgb2: np.ndarray, threshold: int = 3) -> bool:
    """Проверяет, являются ли цвета схожими в пределах порога."""
    return np.all(np.abs(rgb1 - rgb2) < threshold)

def get_city(final_map: Image.Image, coords: GroupCoords, task: Task) -> City:
    """Создает объект города из изображения на основе цветового кодирования."""
    data = np.asarray(final_map)
    height, width = data.shape[:2]
    checked_pixels = np.zeros((height, width), dtype=bool)
    city = City()
    city.objects = []
    city.width = width
    city.height = height
    city.upper_left = (coords.upper_left_latitude, coords.upper_left_longitude)
    city.down_right = (coords.down_right_latitude, coords.down_right_longitude)
    city.x_scale, city.y_scale = calculate_scale(width, height, city.upper_left, city.down_right)
    
    # Создаем словарь для быстрого доступа к типам объектов по цвету
    color_dict = {tuple(color): obj_type for color, obj_type in color_to_name.items()}
    y_progress = 0
    for y in range(height):
        for x in range(width):
            if checked_pixels[y, x]:
                continue
                
            current_color = tuple(data[y, x][:3])
            
            # Проверяем наличие цвета в словаре
            if current_color not in color_dict:
                continue
                
            object_type = color_dict[current_color]
            pixels_list = []
            stack = [(x, y)]
            
            while stack:
                cx, cy = stack.pop()
                
                # Проверка границ и посещенных пикселей
                if (cx < 0 or cx >= width or cy < 0 or cy >= height or 
                    checked_pixels[cy, cx]):
                    continue
                
                # Проверка цвета
                pixel_color = tuple(data[cy, cx][:3])
                if not check_color(np.array(pixel_color), np.array(current_color)):
                    continue
                
                checked_pixels[cy, cx] = True
                pixels_list.append([cx, cy])
                
                # Добавляем соседние пиксели в стек
                stack.append((cx + 1, cy))  # right
                stack.append((cx - 1, cy))  # left
                stack.append((cx, cy + 1))  # down
                stack.append((cx, cy - 1))  # up

                # Диагональные направления
                stack.append((cx - 1, cy - 1))  # left-up
                stack.append((cx + 1, cy - 1))  # right-up
                stack.append((cx - 1, cy + 1))  # left-down
                stack.append((cx + 1, cy + 1))  # right-down
            
            if not pixels_list:
                continue
                
            pixels_array = np.array(pixels_list)
            obj = CityObject()
            obj.type = object_type
            obj.points = pixels_array
            obj.x_pos_center = np.mean(pixels_array[:, 0])
            obj.y_pos_center = np.mean(pixels_array[:, 1])
            obj.square = len(pixels_list)
            city.objects.append(obj)
        new_y_progress = int((y / height) * 100)
        if (new_y_progress - y_progress >= 1):
            task.status_description = f"Прогресс: {new_y_progress}%"
            task.save()
            y_progress = new_y_progress
    
    save_obj_to_pickle(city, 'city', coords.group)
    return city

def make_masks(city: City, group: Group):
    width = city.width
    height = city.height

    # Словарь для хранения массивов каждого типа объекта
    masks = {
        'Water': np.zeros((height, width, 4), dtype=np.uint8),
        'Building': np.zeros((height, width, 4), dtype=np.uint8),
        'Road_Highway': np.zeros((height, width, 4), dtype=np.uint8),
        'Green_Space': np.zeros((height, width, 4), dtype=np.uint8),
        'Infractructure': np.zeros((height, width, 4), dtype=np.uint8),
        'Railway': np.zeros((height, width, 4), dtype=np.uint8)
    }

    colors = {
        'Water': [0, 0, 255, 255],          # Синий
        'Building': [255, 0, 0, 255],       # Красный
        'Road_Highway': [128, 128, 128, 255],     # Серый
        'Green_Space': [0, 128, 0, 255],    # Зеленый
        'Infrastructure': [0, 0, 0, 255], # Черный
        'Railway': [128, 0, 0, 255]
    }

    # Векторизованная отрисовка для каждого объекта
    for obj in city.objects:
        obj_type = obj.type
        color = colors.get(obj_type, None)

        if color is None:
            continue

        points = obj.points.astype(int)
        color = np.array(color, dtype=np.uint8)
        
        if len(points) > 0 and obj_type in masks:
            # Заполняем маску для соответствующего типа объекта
            masks[obj_type][points[:, 1], points[:, 0]] = color

    upload_ids = []

    # Сохраняем каждую маску в отдельный файл
    for obj_type, mask_array in masks.items():
        # Конвертируем массив в изображение
        mask_img = Image.fromarray(mask_array.astype(np.uint8), 'RGBA')
        
        # Сохраняем в файл
        filename = f"{obj_type.lower()}_mask"
        upload_ids.append(save_image_as_file(mask_img, filename, group).upload_id)

    return upload_ids

def get_districts_df_for_city(city: City, k: int, df):
    df_building = df.query('type == "Building"')
    
    X = df_building[['x_pos', 'y_pos']]
    kmeans = KMeans(n_clusters=k)
    kmeans.fit(X)
    districts = list(range(k))
    districts_df = pd.DataFrame({'District': districts})

    df['district'] = kmeans.predict(df[['x_pos', 'y_pos']])

    districts_area = {}
    districts_coverage = []
    building_areas = {}

    for d in districts:
        df_urban = df.query(f'district == {d} and type == "Building"')
        # 1. Находим границы территории
        min_lat = df_urban['latitude'].min()
        max_lat = df_urban['latitude'].max()
        min_lon = df_urban['longitude'].min()
        max_lon = df_urban['longitude'].max()

        # 2. Разница в градусах
        delta_lat = max_lat - min_lat  # разница по широте (север-юг)
        delta_lon = max_lon - min_lon  # разница по долготе (восток-запад)

        # 3. Переводим градусы в метры
        lat_avg = (min_lat + max_lat) / 2  # средняя широта для точности

        # Длина 1° широты в метрах (примерно постоянная)
        lat_to_meters = 111_320  # 1° широты ≈ 111.32 км

        # Длина 1° долготы в метрах (зависит от широты)
        lon_to_meters = 111_320 * np.cos(np.radians(lat_avg))  # учитываем косинус широты

        # 4. Размеры территории в метрах
        length_ns = delta_lat * lat_to_meters  # север-юг (метры)
        length_ew = delta_lon * lon_to_meters  # восток-запад (метры)

        # 5. Площадь территории (прямоугольник)
        total_area_m2 = length_ns * length_ew
        districts_area[d] = total_area_m2

        # 6. Суммарная площадь зданий
        building_areas[d] = df_urban['area_m2'].sum()

    rail_areas = {}

    point_area = city.point_area()
    mask = df["type"] == "Railway"
    df_rail = df[mask]
    # Собираем все точки в один массив
    if df_rail.empty:
        all_points = None
        districts_predicted = None
    else:
        all_points = np.concatenate(df_rail["points"].values)
        # Предсказываем районы для всех точек сразу
        districts_predicted = kmeans.predict(all_points)
    for d in districts:
        total_area_m2 = districts_area[d]
        
        if districts_predicted is not None:
            # Считаем площадь железных дорог
            total_rail_area = np.sum(districts_predicted == d) * point_area
        else:
            total_rail_area = 0
        
        rail_areas[d] = total_rail_area

    inf_areas = {}

    point_area = city.point_area()
    mask = df["type"] == "Infrastructure"
    df_inf = df[mask]
    # Собираем все точки в один массив
    all_points = np.concatenate(df_inf["points"].values)
    # Предсказываем районы для всех точек сразу
    districts_predicted = kmeans.predict(all_points)
    for d in districts:
        total_area_m2 = districts_area[d]
        
        # Считаем площадь инфраструктуры
        total_inf_area = np.sum(districts_predicted == d) * point_area
        
        inf_areas[d] = total_inf_area

    mask = df["type"] == "Road_Highway"
    df_roads = df[mask]
    # Собираем все точки в один массив
    all_points = np.concatenate(df_roads["points"].values)
    # Предсказываем районы для всех точек сразу
    districts_predicted = kmeans.predict(all_points)
    for d in districts:
        total_area_m2 = districts_area[d]
        
        # Считаем площадь дорог
        total_road_area = np.sum(districts_predicted == d) * point_area
        
        # Добавляем итоговый уровень застройки (%)
        districts_coverage.append((building_areas[d] + inf_areas[d] + rail_areas[d] + total_road_area) / total_area_m2)

    districts_df['urban_coverage_ratio'] = districts_coverage
    
    districts_green_coverage = []

    point_area = city.point_area()
    mask = df["type"] == "Green_Space"
    df_green = df[mask]
    # Собираем все точки в один массив
    all_points = np.concatenate(df_green["points"].values)
    # Предсказываем районы для всех точек сразу
    districts_predicted = kmeans.predict(all_points)
    for d in districts:
        total_area_m2 = districts_area[d]
        
        # Считаем площадь зелёных зон
        total_green_area = np.sum(districts_predicted == d) * point_area
        
        # Добавляем итоговый уровень застройки (%)
        districts_green_coverage.append(total_green_area / total_area_m2)

    districts_df['green_coverage_ratio'] = districts_green_coverage

    districts_water_coverage = []

    point_area = city.point_area()
    mask = df["type"] == "Water"
    df_water = df[mask]
    # Собираем все точки в один массив
    all_points = np.concatenate(df_water["points"].values)
    # Предсказываем районы для всех точек сразу
    districts_predicted = kmeans.predict(all_points)
    for d in districts:
        total_area_m2 = districts_area[d]
        
        # Считаем площадь водных зон
        total_water_area = np.sum(districts_predicted == d) * point_area
        
        # Добавляем итоговый уровень застройки (%)
        districts_water_coverage.append(total_water_area / total_area_m2)

    districts_df['water_coverage_ratio'] = districts_water_coverage

    max_distance_meters=50
    max_distance_pixels = max_distance_meters * city.point_area()

    # 1. Подготовка данных дорог
    df_roads = df[df["type"] == "Road_Highway"]
    road_points = np.column_stack((df_roads['x_pos'], df_roads['y_pos'])) if not df_roads.empty else np.empty((0, 2))

    # 2. Создаём KD-дерево для дорог
    road_tree = cKDTree(road_points) if len(road_points) > 0 else None

    results = []

    # 3. Обрабатываем каждый район
    for district in df['district'].unique():
        df_buildings = df[(df['district'] == district) & (df['type'] == 'Building')]
        if df_buildings.empty:
            results.append(0)
            continue
        
        building_coords = np.column_stack((df_buildings['x_pos'], df_buildings['y_pos']))
        
        if road_tree is None:
            results.append(0)
            continue
        
        # Находим расстояния в пикселях
        distances, _ = road_tree.query(building_coords)
        
        # Рассчитываем процент
        pct_near = (distances <= max_distance_pixels).mean()
        results.append(pct_near)
    districts_df['pct_buildings_near_roads_50m'] = results


    max_distance_meters=10
    max_distance_pixels = max_distance_meters * city.point_area()

    # 1. Подготовка данных инфраструктуры
    df_inf = df[df["type"] == "Infrastructure"]
    inf_points = np.column_stack((df_inf['x_pos'], df_inf['y_pos'])) if not df_inf.empty else np.empty((0, 2))

    # 2. Создаём KD-дерево для инфраструктуры
    inf_tree = cKDTree(inf_points) if len(inf_points) > 0 else None

    results = []

    # 3. Обрабатываем каждый район
    for district in df['district'].unique():
        df_buildings = df[(df['district'] == district) & (df['type'] == 'Building')]
        if df_buildings.empty:
            results.append(0)
            continue
        
        building_coords = np.column_stack((df_buildings['x_pos'], df_buildings['y_pos']))
        
        if inf_tree is None:
            results.append(0)
            continue
        
        # Находим расстояния в пикселях
        distances, _ = inf_tree.query(building_coords)
        
        # Рассчитываем процент
        pct_near = (distances <= max_distance_pixels).mean()
        results.append(pct_near)
    districts_df['pct_buildings_near_infrastructure_10m'] = results
    
    # 1. Подготовка данных дорог
    df_roads = df[df["type"] == "Road_Highway"]
    road_points = np.column_stack((df_roads['x_pos'], df_roads['y_pos'])) if not df_roads.empty else np.empty((0, 2))

    # 2. Создаём KD-дерево для дорог
    road_tree = cKDTree(road_points) if len(road_points) > 0 else None

    results = []

    # 3. Обрабатываем каждый район
    for district in df['district'].unique():
        df_buildings = df[(df['district'] == district) & (df['type'] == 'Building')]
        if df_buildings.empty:
            results.append(0)
            continue
        
        building_coords = np.column_stack((df_buildings['x_pos'], df_buildings['y_pos']))
        
        if road_tree is None:
            results.append(0)
            continue
        
        # Находим расстояния в пикселях
        distances, _ = road_tree.query(building_coords)
        
        # Рассчитываем среднее расстояние
        mean_near = distances.mean() * city.point_area()
        results.append(mean_near)
    districts_df['avg_building_distance_to_road_m'] = results

    # 1. Подготовка данных железных дорог
    df_rail = df[df["type"] == "Railway"]
    rail_points = np.column_stack((df_rail['x_pos'], df_rail['y_pos'])) if not df_rail.empty else np.empty((0, 2))

    # 2. Создаём KD-дерево
    rail_tree = cKDTree(rail_points) if len(rail_points) > 0 else None

    results = []

    # 3. Обрабатываем каждый район
    for district in df['district'].unique():
        df_buildings = df[(df['district'] == district) & (df['type'] == 'Building')]
        if df_buildings.empty:
            results.append(-1)
            continue
        
        building_coords = np.column_stack((df_buildings['x_pos'], df_buildings['y_pos']))
        
        if rail_tree is None:
            results.append(-1)
            continue
        
        # Находим расстояния в пикселях
        distances, _ = rail_tree.query(building_coords)
        
        # Рассчитываем среднее расстояние
        mean_near = distances.mean() * city.point_area()
        results.append(mean_near)
    districts_df['avg_building_distance_to_railway_m'] = results

    # Расчёт уровня шума
    L_road = 70  # Уровень шума у дороги (10 м), примерное
    districts_df["noise_reduction_distance"] = 20 * np.log10(districts_df["avg_building_distance_to_road_m"] / 10)
    districts_df["noise_reduction_green"] = 5 * districts_df["green_coverage_ratio"]  # Зелёные зоны снижают шум
    districts_df["noise_amplification_urban"] = 10 * districts_df["urban_coverage_ratio"]  # Город усиливает шум
    districts_df["estimated_noise_level_road"] = L_road - districts_df["noise_reduction_distance"] - districts_df["noise_reduction_green"] + districts_df["noise_amplification_urban"]

    # Расчёт уровня шума от железных дорог
    L_railway = 85  # Уровень шума у ж/д путей (10 м)
    if (districts_df["avg_building_distance_to_railway_m"] == -1).all():
        districts_df["noise_reduction_railway_distance"] = -1
        districts_df["estimated_railway_noise"] = 0
    else:
        # Расчёт для городов с железными дорогами
        districts_df["noise_reduction_railway_distance"] = 20 * np.log10(districts_df["avg_building_distance_to_railway_m"] / 10)
        districts_df["estimated_railway_noise"] = (
            L_railway
            - districts_df["noise_reduction_railway_distance"] 
            - districts_df["noise_reduction_green"] 
            + districts_df["noise_amplification_urban"])
    
    # Рассчитаем общий шум (RMS)
    districts_df["total_noise"] = np.sqrt(districts_df["estimated_noise_level_road"]**2 + districts_df["estimated_railway_noise"]**2)

    # Нормализация метрик
    districts_df["noise_score"] = 1 - (districts_df["total_noise"] / districts_df["total_noise"].max())
    districts_df["green_score"] = districts_df["green_coverage_ratio"]
    districts_df["urban_score"] = 1 - districts_df["urban_coverage_ratio"]
    districts_df["infra_score"] = 1 - (districts_df["pct_buildings_near_roads_50m"] + districts_df["pct_buildings_near_infrastructure_10m"]) / 2

    # Веса факторов (можно настроить)
    weights = {
        "noise": 0.4,
        "green": 0.3,
        "urban": 0.2,
        "infra": 0.1
    }

    # Итоговый индекс
    districts_df["ergonomics_index"] = (
        weights["noise"] * districts_df["noise_score"] +
        weights["green"] * districts_df["green_score"] +
        weights["urban"] * districts_df["urban_score"] +
        weights["infra"] * districts_df["infra_score"]
    )

    return districts_df

def get_weather_data_temp(latitude, longitude, start_date, end_date):
    """Получение данных о погоде с API Open-Meteo"""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'start_date': start_date,
        'end_date': end_date,
        'hourly': 'temperature_2m,relative_humidity_2m'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Ошибка при запросе к API: {response.status_code}")

def calculate_monthly_averages_temp(weather_data):
    """Расчет среднемесячных температуры и влажности"""
    hourly_data = weather_data.get('hourly', {})
    times = hourly_data.get('time', [])
    temperatures = hourly_data.get('temperature_2m', [])
    humidities = hourly_data.get('relative_humidity_2m', [])
    
    if not times or not temperatures or not humidities:
        raise ValueError("Недостаточно данных для расчета")
    
    # Словари для хранения данных по месяцам
    monthly_temp = defaultdict(list)
    monthly_humidity = defaultdict(list)
    
    # Группировка данных по месяцам
    for time_str, temp, humidity in zip(times, temperatures, humidities):
        try:
            date = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
            month_key = f"{date.year}-{date.month:02d}"  # Формат "ГГГГ-ММ"
            monthly_temp[month_key].append(temp)
            monthly_humidity[month_key].append(humidity)
        except ValueError as e:
            print(f"Ошибка при обработке даты {time_str}: {e}")
            continue
    
    # Расчет средних значений для каждого месяца
    results = []
    for month in sorted(monthly_temp.keys()):
        avg_temp = sum(monthly_temp[month]) / len(monthly_temp[month])
        avg_humidity = sum(monthly_humidity[month]) / len(monthly_humidity[month])
        results.append({
            'month': month,
            'avg_temperature': round(avg_temp, 2),
            'avg_humidity': round(avg_humidity, 2),
            'readings_count': len(monthly_temp[month])
        })
    
    return results

def get_month_temp(latitude, longitude):
    start_date,end_date = "2023-01-01", "2023-12-31"
    try:
        # Получаем данные о погоде
        weather_data = get_weather_data_temp(latitude, longitude, start_date, end_date)
        
        # Рассчитываем средние значения по месяцам
        monthly_averages = calculate_monthly_averages_temp(weather_data)
        
        return monthly_averages
        
    except Exception as e:
        print(f"Не удалось загрузить данные о температуре: {e}")
        return [{'avg_temperature': 0, 'avg_humidity': 0} for _ in range(12)]

def get_weather_data_pm(latitude, longitude, start_date, end_date):
    """Получение данных о погоде с API Open-Meteo"""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'start_date': start_date,
        'end_date': end_date,
        'hourly': 'pm2_5'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Ошибка при запросе к API: {response.status_code}")

def calculate_monthly_averages_pm(weather_data):
    """Расчет среднемесячных pm2.5"""
    hourly_data = weather_data.get('hourly', {})
    times = hourly_data.get('time', [])
    pm2_5 = hourly_data.get('pm2_5', [])
    
    if not times or not pm2_5:
        raise ValueError("Недостаточно данных для расчета")
    
    # Словари для хранения данных по месяцам
    monthly_pm2_5 = defaultdict(list)
    
    # Группировка данных по месяцам
    for time_str, pm in zip(times, pm2_5):
        try:
            date = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
            month_key = f"{date.year}-{date.month:02d}"  # Формат "ГГГГ-ММ"
            monthly_pm2_5[month_key].append(pm)
        except ValueError as e:
            print(f"Ошибка при обработке даты {time_str}: {e}")
            continue
    
    # Расчет средних значений для каждого месяца
    results = []
    for month in sorted(monthly_pm2_5.keys()):
        avg_pm = sum(monthly_pm2_5[month]) / len(monthly_pm2_5[month])
        results.append({
            'month': month,
            'avg_pm2_5': round(avg_pm, 2),
            'readings_count': len(monthly_pm2_5[month])
        })
    
    return results

def get_month_pm(latitude, longitude):
    start_date,end_date = "2023-01-01", "2023-12-31"

    try:
        # Получаем данные о погоде
        weather_data = get_weather_data_pm(latitude, longitude, start_date, end_date)
        
        # Рассчитываем средние значения по месяцам
        monthly_averages_pm = calculate_monthly_averages_pm(weather_data)
        
        return monthly_averages_pm
        
    except Exception as e:
        print(f"Не удалось загрузить данные о загрязнении воздуха: {e}")
        return [{'avg_pm2_5': 0} for _ in range(12)]

def make_kde_plots(districts_df : pd.DataFrame, df : pd.DataFrame, group: Group):
    keys = ['urban_coverage_ratio', 'green_coverage_ratio', 'water_coverage_ratio', 
            'pct_buildings_near_roads_50m', 'pct_buildings_near_infrastructure_10m',
            'ergonomics_index']
    
    upload_ids = []

    for key in keys:
        # Создаем цветовую карту
        cmap = LinearSegmentedColormap.from_list('coverage', ['red', 'yellow', 'green'])
        norm = plt.Normalize(vmin=districts_df[key].min(), 
                            vmax=districts_df[key].max())

        # Создаем график
        fig, ax = plt.subplots(figsize=(12, 10))

        # Для каждого района строим контурную заливку
        for _, row in districts_df.iterrows():
            district = row['District']
            coverage = row[key]
            
            # Берем все точки данного района
            points = df[df['district'] == district][['x_pos', 'y_pos']].values
            
            if len(points) > 10:  # Минимальное количество точек для KDE
                # Создаем KDE модель
                kde = KernelDensity(bandwidth=50, kernel='gaussian')  # Подберите bandwidth под ваш масштаб
                kde.fit(points)
                
                # Создаем сетку для визуализации
                x_min, x_max = points[:, 0].min()-100, points[:, 0].max()+100
                y_min, y_max = points[:, 1].min()-100, points[:, 1].max()+100
                xx, yy = np.mgrid[x_min:x_max:100j, y_min:y_max:100j]
                grid = np.vstack([xx.ravel(), yy.ravel()]).T
                
                # Вычисляем плотность
                log_density = kde.score_samples(grid)
                zz = np.exp(log_density).reshape(xx.shape)
                
                # Рисуем контурную заливку
                ax.contourf(xx, yy, zz, levels=10, colors=[cmap(norm(coverage))], alpha=0.5)
                
                # Добавляем границу района (контур)
                ax.contour(xx, yy, zz, levels=[0.01], colors=['black'], linewidths=1)
                
                # Добавляем номер района в центроид
                centroid = points.mean(axis=0)
                ax.text(centroid[0], centroid[1], f"D{district}\n{coverage:.3f}", 
                        ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

        # Добавляем цветовую шкалу
        sm = ScalarMappable(cmap=cmap, norm=norm)
        plt.colorbar(sm, ax=ax, label=key)

        # Настройки графика
        ax.set_title('District '+key)
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        ax.invert_yaxis()  # инвертируем ось Y (если нужно)
        ax.grid(True, linestyle='--', alpha=0.3)

        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)

        upload_ids.append(save_buffer_image_as_file(buf, f'{key}_plot_{districts_df.shape[0]}', group).upload_id)

        plt.close(fig)
    
    return upload_ids

import joblib
base_path = __file__.replace('methods.py', '')
scaler = joblib.load(os.path.join(base_path, 'models', 'scaler.pkl'))
model_living = joblib.load(os.path.join(base_path, 'models', 'model_living.pkl'))
model_infra = joblib.load(os.path.join(base_path, 'models', 'model_infra.pkl'))
model_green = joblib.load(os.path.join(base_path, 'models', 'model_green.pkl'))

def analyze_city(city: City, group: Group, k: int, has_generated_masks: bool):
    df = city.as_dataframe()
    results = {}
    if not has_generated_masks:
        masks_upload_ids = make_masks(city, group)
        results['masks_ids'] = masks_upload_ids
    districts_df = get_districts_df_for_city(city, k=k, df=df)
    districts_plots_uploads_ids = make_kde_plots(districts_df, df, group)
    results['kde_plots_ids'] = districts_plots_uploads_ids
    latitude, longitude = city.get_center_coordinates()
    values = districts_df.drop(["District", "noise_score", 'green_score', 'urban_score', 'infra_score', 'ergonomics_index', 'total_noise'], axis=1).mean()
    monthly_temp = get_month_temp(latitude, longitude)
    monthly_pm = get_month_pm(latitude, longitude)
    t = list()
    h = list()
    for month_data in monthly_temp:
        t.append(month_data['avg_temperature'])
        h.append(month_data['avg_humidity'])

    pm = list()
    for month_data in monthly_pm:
        pm.append(month_data['avg_pm2_5'])
    
    for_prediction = list(values)+t+h+pm
    scaled = scaler.transform([for_prediction])
    results['infra_score'] = model_infra.predict(scaled)[0]
    results['green_score'] = model_green.predict(scaled)[0]
    results['living_score'] = model_living.predict(scaled)[0]
    return results

logger = get_task_logger(__name__)

@shared_task() 
def process_map_group(task_id: int, files_dict: dict[str, str], coords_id: int, k: int = 2):
    try:
        task = Task.objects.get(task_id=task_id)
        coords = GroupCoords.objects.get(id=coords_id)
        
        print(files_dict)

        # Восстанавливаем файлы из путей
        files: dict[str, File] = {}
        for filename, file_path in files_dict.items():
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    files[filename] = File(f)  # Теперь это снова файловый объект
            else:
                raise FileNotFoundError(f"Файл {file_path} не найден")

        city_map = None
        buildings_map = None
        railways_map = None

        city_map_cropped = None
        buildings_map_cropped = None
        railways_map_cropped = None

        final_map = None
        city_file_pickle = None

        has_generated_masks = False
        has_generated_for_k = False

        for f in files:
            if f.startswith('city_map_image_cropped'):
                city_map_cropped = files[f]
            elif f.startswith('buildings_map_image_cropped'):
                buildings_map_cropped = files[f]
            elif f.startswith('railways_map_image_cropped'):
                railways_map_cropped = files[f]
            elif f.startswith('city_map'):
                city_map = files[f]
            elif f.startswith('buildings_map'):
                buildings_map = files[f]
            elif f.startswith('railways_map'):
                railways_map = files[f]
            elif f.startswith('final_map'):
                final_map = files[f]
            elif f == 'city.pickle':
                city_file_pickle = files[f]
            elif f.startswith(f'urban_coverage_ratio_plot_{k}'):
                has_generated_for_k = True
            elif f.startswith(f'building_mask'):
                has_generated_masks = True
        
        task.status_description = 'Карты обрезаются'
        task.save()

        if city_map_cropped is None or buildings_map_cropped is None:
            maps = crop_maps(coords.group, city_map, buildings_map, railways_map)
            city_map_cropped = maps[0]
            
            buildings_map_cropped = maps[1]
            if len(maps) > 2:
                railways_map_cropped = maps[2]
        else:
            city_map_cropped = open_image(city_map_cropped)
            buildings_map_cropped = open_image(buildings_map_cropped)

            if railways_map_cropped is not None:
                railways_map_cropped = open_image(railways_map_cropped)


        del city_map
        del buildings_map
        del railways_map
        gc.collect()

        task.status_description = 'Делается итоговая карта с цветовым кодированием'
        task.save()

        if final_map is None:
            final_map = make_final_map(coords.group, city_map_cropped, buildings_map_cropped, railways_map_cropped)
        else:
            final_map = open_image(final_map)


        del city_map_cropped
        del buildings_map_cropped
        del railways_map_cropped
        gc.collect()

        if final_map.height > 6500 or final_map.width > 6500:
            # Высчитываем коэффициент масштабирования
            scaling_factor = min(6500 / final_map.width, 6500 / final_map.height)
            
            # Высчитываем новые размеры сторон
            new_width = int(final_map.width * scaling_factor)
            new_height = int(final_map.height * scaling_factor)
            
            # Масштабируем изображение
            final_map = final_map.resize((new_width, new_height))

        task.status_description = 'Переходим к созданию объектной карты города'
        task.save()

        city: City = None

        if city_file_pickle is None:
            city = get_city(final_map, coords, task)
        else:
            with city_file_pickle.open('rb') as file:
                city = pickle.load(file)
        
        task.status_description = 'Объектная карта города создана. Анализируем...'
        task.save()

        del final_map
        gc.collect()

        if not has_generated_for_k:
            analyze_results = analyze_city(city, coords.group, k, has_generated_masks)
        

            task.status = Task.StatusChoices.FINISHED
            task.status_description = "Карта успешно проанализирована."
            task.save()

            task_results = TaskResult()
            task_results.task = task
            task_results.result = analyze_results
            task_results.save()
        else:
            task.status = Task.StatusChoices.FAILED
            task.status_description = "Карта уже была проанализирована на таком количестве кластеров."
            task.save()

    except Exception as e:
        error_traceback = traceback.format_exc()
        task = Task.objects.get(task_id=task_id)
        task.status = Task.StatusChoices.FAILED
        task.status_description = f'{str(e)}\n\nTraceback:\n{error_traceback}'
        task.save()

        logger.error(f"Task {task_id} failed: {str(e)}\n{error_traceback}")
        
        