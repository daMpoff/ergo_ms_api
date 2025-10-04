import os
import re
import logging
import subprocess
import shutil
import signal
import time
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from io import BytesIO
from PIL import Image
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import matplotlib
matplotlib.use('Agg')

# Кроссплатформенная блокировка файлов: fcntl на Unix, msvcrt на Windows
try:
    import fcntl  # type: ignore
except Exception:
    fcntl = None  # type: ignore
try:
    import msvcrt  # type: ignore
except Exception:
    msvcrt = None  # type: ignore

def _acquire_file_lock(lockf):
    """Ставит эксклюзивную блокировку на файл по возможности.
    На Unix — через fcntl, на Windows — через msvcrt, иначе — no-op.
    """
    try:
        if fcntl is not None:
            try:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass
        elif os.name == 'nt' and msvcrt is not None:
            try:
                # Блокируем 1 байт файла
                msvcrt.locking(lockf.fileno(), msvcrt.LK_LOCK, 1)
            except Exception:
                pass
    except Exception:
        pass

def _release_file_lock(lockf):
    """Снимает блокировку с файла, если ранее ставили."""
    try:
        if fcntl is not None:
            try:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        elif os.name == 'nt' and msvcrt is not None:
            try:
                msvcrt.locking(lockf.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
    except Exception:
        pass

# Проверяем доступность LibreOffice или unoconv для конвертации
def check_conversion_tools():
    """Проверяет доступность инструментов для конвертации DOCX в PDF"""
    tools = {
        'libreoffice': False,
        'unoconv': False,
        'soffice': False
    }
    
    # Проверяем LibreOffice
    for cmd in ['libreoffice', 'soffice']:
        if shutil.which(cmd):
            tools[cmd] = True
            
    # Проверяем unoconv
    if shutil.which('unoconv'):
        tools['unoconv'] = True
    
    return tools

CONVERSION_TOOLS = check_conversion_tools()

# Настраиваем логгер для генератора отчетов
logger = logging.getLogger('celery.task.porosity_analysis.reports')


class PorosityReportGenerator:
    """Генератор отчетов по анализу пористости"""
    
    def __init__(self, analysis, in_memory_results: Optional[Dict] = None):
        """
        Инициализация генератора отчетов
        
        Args:
            analysis: Объект PorosityAnalysis из базы данных
        """
        self.analysis = analysis
        self.results_dir = analysis.results_directory
        self.in_memory_results = in_memory_results or {}
        
    def _compress_image_for_docx(self, image: Image.Image, target_width_inches: float = 5.5, target_dpi: int = 220) -> BytesIO:
        """
        Подготавливает изображение для вставки в DOCX с минимальным размером файла
        без заметной потери качества.

        - Масштабирует до нужной ширины под заданный DPI, сохраняя пропорции
        - Конвертирует в JPEG (RGB, без альфы) с параметрами для высокого качества

        Args:
            image: PIL.Image
            target_width_inches: целевая ширина изображения в документе
            target_dpi: расчетное DPI для целевой ширины

        Returns:
            BytesIO: байтовый поток с перекодированным изображением
        """
        try:
            # Приводим режим и убираем прозрачность (если есть)
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                background = Image.new("RGB", image.size, (255, 255, 255))
                alpha = image.convert("RGBA")
                background.paste(alpha, mask=alpha.split()[-1])
                work_img = background
            else:
                work_img = image.convert("RGB") if image.mode != "RGB" else image

            # Вычисляем целевую ширину в пикселях
            target_width_px = max(1, int(round(target_width_inches * target_dpi)))
            orig_w, orig_h = work_img.size

            # Масштабируем только если исходник шире целевого
            if orig_w > target_width_px:
                scale = target_width_px / float(orig_w)
                new_size = (target_width_px, max(1, int(round(orig_h * scale))))
                work_img = work_img.resize(new_size, Image.LANCZOS)

            bio = BytesIO()
            # JPEG: высокое качество, оптимизация, прогрессивность, без даунсэмплинга хромы
            work_img.save(
                bio,
                format="JPEG",
                quality=88,
                optimize=True,
                progressive=True,
                subsampling=1  # 4:4:4
            )
            bio.seek(0)
            return bio
        except Exception as e:
            # Фолбек: сохраняем как PNG в поток
            logger.warning(f"Не удалось сжать изображение в JPEG, используем PNG: {e}")
            bio = BytesIO()
            try:
                png_img = image
                if png_img.mode in ("RGBA", "LA"):
                    # Сохраняем альфу для PNG
                    png_img.save(bio, format="PNG", optimize=True)
                else:
                    png_img.convert("RGB").save(bio, format="PNG", optimize=True)
            except Exception:
                # Последний фолбек: как есть
                image.save(bio, format="PNG")
            bio.seek(0)
            return bio

    def _get_image_descriptions(self) -> Dict[str, Dict[str, str]]:
        """
        Возвращает детальные описания для каждого изображения с метриками
        
        Returns:
            Dict[str, Dict[str, str]]: Словарь с описаниями и метриками для каждого изображения
        """
        results = self.in_memory_results
        
        # Безопасное получение значений с дефолтными значениями
        num_pores = results.get('number_of_pores', 0)
        porosity = results.get('porosity_percentage', 0.0)
        scale_value = self.analysis.scale_value if self.analysis.scale_value else 0
        pixels_per_micron = results.get('pixels_per_micron', 0)
        
        # Подсчет исключенных областей
        try:
            exclude_mask = results.get('exclude_mask')
            lines_exclude_mask = results.get('lines_exclude_mask')
            anomalies_exclude_mask = results.get('anomalies_exclude_mask')
            scale_exclude_mask = results.get('scale_exclude_mask')
            
            if exclude_mask is not None:
                import numpy as np
                total_pixels = exclude_mask.size
                excluded_pixels = np.sum(~exclude_mask)
                excluded_percent = (excluded_pixels / total_pixels) * 100
            else:
                excluded_pixels = 0
                excluded_percent = 0
                
            if lines_exclude_mask is not None:
                lines_excluded = np.sum(~lines_exclude_mask)
            else:
                lines_excluded = 0
                
            if anomalies_exclude_mask is not None:
                anomalies_excluded = np.sum(~anomalies_exclude_mask)
            else:
                anomalies_excluded = 0
        except:
            excluded_pixels = excluded_percent = lines_excluded = anomalies_excluded = 0
        
        # Статистика по размерам пор
        mean_size = results.get('mean_pore_size_microns', 0)
        max_size = results.get('max_pore_size_microns', 0)
        min_size = results.get('min_pore_size_microns', 0)
        pore_density = results.get('pore_density', 0)
        avg_interpore_dist = results.get('average_interpore_distance', 0)
        
        # Данные об ориентации
        orientation_data = results.get('pore_orientation', {})
        has_preferred_direction = orientation_data.get('has_preferred_direction', False)
        mean_orientation = orientation_data.get('mean_orientation', 0)
        orientation_strength = orientation_data.get('orientation_strength', 0)
        std_orientation_deg = orientation_data.get('std_orientation', 0)
        
        # Данные о формах
        pore_shapes = results.get('pore_shapes')
        shape_stats = {}
        if pore_shapes is not None and hasattr(pore_shapes, 'empty') and not pore_shapes.empty:
            shape_counts = pore_shapes['Тип формы'].value_counts()
            total_shapes = len(pore_shapes)
            for shape, count in shape_counts.items():
                shape_stats[shape] = (count, count/total_shapes*100)
        
        descriptions = {
            'original': {
                'title': 'Исходное изображение',
                'description': f'Исходное изображение микроскопии для анализа пористости. Масштаб: {scale_value} мкм.'
            },
            'scale_bar': {
                'title': 'Изображение с обнаруженной шкалой',
                'description': f'Автоматически обнаруженная масштабная линейка. Определенное значение: {scale_value} мкм, соответствует {pixels_per_micron:.2f} пикселей/мкм. Область шкалы исключена из анализа пористости.'
            },
            'figure1': {
                'title': 'Этапы обработки контраста',
                'description': f'Слева: исходное изображение в оттенках серого. Справа: изображение после адаптивного улучшения контраста методом CLAHE (Contrast Limited Adaptive Histogram Equalization) и ограничением контраста 2.0 для лучшего выделения пор. Затем применяется билатеральная фильтрация для шумоподавления с сохранением краев.'
            },
            'figure2': {    
                'title': 'Исключенные области',
                'description': f'Визуализация областей, исключенных из анализа. Общий процент исключенных областей: {excluded_percent:.1f}%. Исключены линейные структуры, аномальные области и масштабная шкала.'
            },
            'figure3': {
                'title': 'Текстурный анализ',
                'description': f'Слева: карта локальной энтропии для анализа текстуры. Справа: результат K-means кластеризации (K=3 кластера) для сегментации изображения на фон, материал и поры. Кластеризация выполняется по признакам интенсивности и локальной энтропии для повышения точности сегментации.'
            },
            'figure4': {
                'title': 'Бинарная маска и результат анализа',
                'description': f'Слева: бинарная маска обнаруженных пор после морфологического открытия и удаления мелких объектов. Справа: маркированные поры после применения алгоритма водораздела для разделения слипшихся пор. Обнаружено пор: {num_pores}. Площадь всех пор составляет {(num_pores * mean_size if num_pores > 0 else 0):.1f} мкм².'
            },
            'figure5': {
                'title': 'Наложение результатов на исходное изображение',
                'description': f'Визуализация обнаруженных пор (красный цвет) на исходном изображении. Измеренная пористость: {porosity:.2f}%. Плотность пор: {pore_density:.4f} пор/мкм².'
            },
            'dist1': {
                'title': 'Распределение размеров пор',
                'description': f'Гистограмма распределения пор по диаметрам. Средний размер: {mean_size:.2f} мкм, минимальный: {min_size:.2f} мкм, максимальный: {max_size:.2f} мкм. Общее количество пор: {num_pores}.'
            },
            'dist2': {
                'title': 'Межпоровые расстояния',
                'description': f'Диаграмма Вороного и визуализация минимальных межпоровых расстояний между центрами пор. Среднее расстояние между соседними порами: {avg_interpore_dist:.2f} мкм. Максимальное расстояние в выборке: {results.get("interpore_distances", [0])[-1] if len(results.get("interpore_distances", [])) > 0 else 0:.2f} мкм, минимальное: {min(results.get("interpore_distances", [0])) if len(results.get("interpore_distances", [])) > 0 else 0:.2f} мкм.'
            },
            'rose': {
                'title': 'Роза направлений пор',
                'description': f'Полярная диаграмма распределения ориентации пор с интервалами по 10° (всего 18 интервалов в диапазоне 0-180°). {"Обнаружено предпочтительное направление: " + str(mean_orientation) + "° с силой направленности " + str(orientation_strength) + ". Стандартное отклонение ориентации: " + str(std_orientation_deg) + "°" if has_preferred_direction else "Предпочтительное направление не выявлено, ориентация пор равномерная с силой направленности " + str(orientation_strength) + "."}.'
            },
            'hist': {
                'title': 'Гистограмма ориентации пор',
                'description': f'Распределение ориентации пор в диапазоне 0-180°, взвешенное по площади пор (всего 18 интервалов по 10°). Учитываются только поры площадью более среднего значения для исключения влияния мелких артефактов. Анализ показывает {"анизотропную структуру с преимущественной ориентацией в направлении " + str(mean_orientation) + "°" if has_preferred_direction else "изотропную структуру без выраженной направленности"}.'
            },
            'shapes': {
                'title': 'Анализ форм пор',
                'description': f'Слева: распределение пор по типам форм. Справа: визуализация форм пор в виде эллипсов. ' + 
                             (f"Круглых: {shape_stats.get('Круглая', (0, 0))[1]:.1f}%, овальных: {shape_stats.get('Овальная', (0, 0))[1]:.1f}%, удлиненных: {shape_stats.get('Удлиненная', (0, 0))[1]:.1f}%." if shape_stats else "")
            },
            'circ': {
                'title': 'Распределение кругового фактора',
                'description': f'Гистограмма распределения кругового фактора пор в 20 интервалах (4πS/P², где S - площадь, P - периметр). Значения близкие к 1.0 указывают на круглые поры, меньшие значения - на вытянутые или неправильные формы. Граничные значения: >0.85 - круглые поры, 0.65-0.85 - овальные поры, <0.65 - вытянутые и неправильные формы.'
            },
            'ellipt': {
                'title': 'Зависимость эллиптичности от площади',
                'description': f'Диаграмма рассеяния в логарифмическом масштабе по оси X, показывающая связь между размером пор (мкм²) и их эллиптичностью (отношение большой оси к малой оси эллипса). Значения эллиптичности >1.5 указывают на вытянутые поры, 1.0-1.5 на овальные, близкие к 1.0 - на круглые. Цветовая кодировка соответствует типам форм пор.'
            }
        }
        
        return descriptions

    def _format_number(self, value: float) -> str:
        """
        Форматирует числа: если меньше 1, то показывает 2 знака после запятой
        """
        try:
            if isinstance(value, str):
                return value
            if value < 1.0:
                return f"{value:.2f}"
            elif value < 10.0:
                return f"{value:.1f}"
            else:
                return f"{value:.0f}"
        except (TypeError, ValueError):
            return str(value)

    def _get_pore_clusters_data(self) -> Dict:
        """
        Получает данные о группах пор из результатов анализа
        
        Returns:
            Dict с данными о группах пор
        """
        results = self.in_memory_results
        pore_properties = results.get('pore_properties', [])
        microns_per_pixel = results.get('microns_per_pixel', 1.0)
        
        import numpy as np
        
        # Вычисляем статистику по площадям пор
        areas_pixels = [prop.area for prop in pore_properties]
        areas_microns = [area * (microns_per_pixel ** 2) for area in areas_pixels]
        
        # Вычисляем размеры осей (проекций)
        minor_axes_microns = []
        major_axes_microns = []
        
        for prop in pore_properties:
            if hasattr(prop, 'minor_axis_length') and hasattr(prop, 'major_axis_length'):
                minor_axis = prop.minor_axis_length * microns_per_pixel
                major_axis = prop.major_axis_length * microns_per_pixel
                # Проверяем что значения не нулевые
                if minor_axis > 0 and major_axis > 0:
                    minor_axes_microns.append(minor_axis)
                    major_axes_microns.append(major_axis)
        
        # Если нет данных об осях, вычисляем из площади
        if len(minor_axes_microns) < len(areas_microns) * 0.5:
            minor_axes_microns = []
            major_axes_microns = []
            for area in areas_microns:
                radius = np.sqrt(area / np.pi)
                minor_axes_microns.append(radius * 1.6)
                major_axes_microns.append(radius * 2.2)
        
        return {
            'min_area': np.min(areas_microns),
            'max_area': np.max(areas_microns),
            'mean_area': np.mean(areas_microns),
            'min_minor_axis': np.min(minor_axes_microns),
            'max_minor_axis': np.max(minor_axes_microns),
            'mean_minor_axis': np.mean(minor_axes_microns),
            'min_major_axis': np.min(major_axes_microns),
            'max_major_axis': np.max(major_axes_microns),
            'mean_major_axis': np.mean(major_axes_microns)
        }


    def _get_analyzed_area_data(self) -> Dict:
        """
        Получает данные об анализируемой площади
        
        Returns:
            Dict с данными о площади анализа
        """
        results = self.in_memory_results
        exclude_mask = results.get('exclude_mask')
        microns_per_pixel = results.get('microns_per_pixel', 1.0)
        
        import numpy as np
        total_pixels = np.sum(exclude_mask)
        area_microns2 = total_pixels * (microns_per_pixel ** 2)
        area_mm2 = area_microns2 / (1000 ** 2)
        
        return {
            'area_mm2': area_mm2,
            'area_microns2': area_microns2
        }

    def _get_detailed_analysis_data(self) -> Dict:
        """
        Получает детальные данные анализа включая распределение по размерам
        
        Returns:
            Dict с детальными данными анализа
        """
        results = self.in_memory_results
        
        # Основные показатели из результатов
        num_pores = results.get('number_of_pores', 0)
        pore_properties = results.get('pore_properties', [])
        microns_per_pixel = results.get('microns_per_pixel', 1.0)
        porosity_percentage = results.get('porosity_percentage', 0)
        
        # Вычисляем общую площадь пор
        areas_pixels = [prop.area for prop in pore_properties]
        total_pore_area = sum(areas_pixels) * (microns_per_pixel ** 2)
        
        # Диаметры пор
        pore_diameters_microns = results.get('pore_diameters_microns', [])
        
        import numpy as np
        min_diameter = np.min(pore_diameters_microns)
        max_diameter = np.max(pore_diameters_microns)
        mean_diameter = np.mean(pore_diameters_microns)
        std_diameter = np.std(pore_diameters_microns)
        median_diameter = np.median(pore_diameters_microns)
        
        # Получаем распределение по размерам
        size_distribution_df = results.get('pore_size_distribution')
        
        # Дополняем распределение процентными долями если их нет
        size_distribution_df = self._calculate_distribution_percentages(size_distribution_df)
        
        return {
            'total_objects': num_pores,
            'total_pore_area': total_pore_area,
            'area_fraction': porosity_percentage,
            'min_diameter': min_diameter,
            'max_diameter': max_diameter,
            'mean_diameter': mean_diameter,
            'std_diameter': std_diameter,
            'median_diameter': median_diameter,
            'size_distribution': size_distribution_df
        }


    def _calculate_distribution_percentages(self, df):
        """
        Вычисляет процентные доли для распределения по размерам
        
        Args:
            df: DataFrame с данными распределения
            
        Returns:
            DataFrame с добавленными процентными долями
        """
        import pandas as pd
        
        # Создаем копию DataFrame
        df_copy = df.copy()
        
        # Вычисляем общие суммы
        total_count = df_copy['Количество пор'].sum()
        total_area = df_copy['Общая площадь (мкм²)'].sum()
        total_volume = df_copy['Общий объем (мкм³)'].sum()
        
        # Добавляем процентные доли
        df_copy['Доля по количеству (%)'] = (df_copy['Количество пор'] / total_count * 100)
        df_copy['Доля по площади (%)'] = (df_copy['Общая площадь (мкм²)'] / total_area * 100)
        df_copy['Доля по объему (%)'] = (df_copy['Общий объем (мкм³)'] / total_volume * 100)
        
        return df_copy

    def _get_available_images(self) -> List[tuple]:
        """
        Получает список доступных изображений для отчета
        
        Returns:
            List[tuple]: Список кортежей (путь_к_файлу, описание, ключ)
        """
        available_images = []
        descriptions = self._get_image_descriptions()

        # 1) Источник: in-memory изображения из результатов анализа
        mem_images = [
            ('original', 'Исходное изображение', self.in_memory_results.get('original_image')),
            ('scale_bar', 'Изображение с обнаруженной шкалой', self.in_memory_results.get('image_with_scale')),
            ('figure1', 'Этапы обработки контраста', self.in_memory_results.get('figure1_contrast')),
            ('figure2', 'Исключенные области', self.in_memory_results.get('figure2_excluded_areas')),
            ('figure3', 'Текстурный анализ', self.in_memory_results.get('figure3_texture_clusters')),
            ('figure4', 'Бинарная маска и результат анализа', self.in_memory_results.get('figure4_mask_result')),
            ('figure5', 'Наложение результатов на исходное изображение', self.in_memory_results.get('figure5_overlay')),
            ('dist1', 'Распределение размеров пор', self.in_memory_results.get('pore_size_distribution_fig')),
            ('dist2', 'Межпоровые расстояния', self.in_memory_results.get('interpore_distances_fig')),
            ('rose', 'Роза направлений пор', self.in_memory_results.get('pore_orientation_rose_fig')),
            ('hist', 'Гистограмма ориентации пор', self.in_memory_results.get('pore_orientation_hist_fig')),
            ('shapes', 'Анализ форм пор', self.in_memory_results.get('pore_shapes_analysis_fig')),
            ('circ', 'Распределение кругового фактора', self.in_memory_results.get('circularity_distribution_fig')),
            ('ellipt', 'Зависимость эллиптичности от площади', self.in_memory_results.get('ellipticity_vs_area_fig'))
        ]

        # Список найденных ключей для отслеживания
        found_keys = set()
        
        for key, description, img in mem_images:
            pil_img = None
            try:
                if img is None:
                    logger.debug(f"Изображение {key} отсутствует в памяти")
                    continue
                # numpy.ndarray -> PIL.Image
                if hasattr(img, 'shape'):
                    pil_img = Image.fromarray(img)
                elif isinstance(img, Image.Image):
                    pil_img = img
                elif isinstance(img, (bytes, bytearray)):
                    pil_img = Image.open(BytesIO(img))
                else:
                    logger.debug(f"Неподдерживаемый тип изображения {key}: {type(img)}")
                    continue
                available_images.append((pil_img, description, key))
                found_keys.add(key)
                logger.debug(f"Добавлено изображение {key} из памяти")
            except Exception as e:
                logger.warning(f"Ошибка при обработке изображения {key}: {e}")
                continue

        # 2) Фолбек: для изображений, которых нет в памяти, пробуем файлы на диске
        images_to_check = [
            ('original', 'Исходное изображение', self.analysis.original_image_path),
            ('scale_bar', 'Изображение с обнаруженной шкалой', os.path.join(self.results_dir, 'image_with_scale_bar.png')),
            ('figure1', 'Этапы обработки контраста', os.path.join(self.results_dir, 'figure1_contrast.png')),
            ('figure2', 'Исключенные области', os.path.join(self.results_dir, 'figure2_excluded_areas.png')),
            ('figure3', 'Текстурный анализ', os.path.join(self.results_dir, 'figure3_texture_clusters.png')),
            ('figure4', 'Бинарная маска и результат анализа', os.path.join(self.results_dir, 'figure4_mask_result.png')),
            ('figure5', 'Наложение результатов на исходное изображение', os.path.join(self.results_dir, 'figure5_overlay.png')),
            ('dist1', 'Распределение размеров пор', os.path.join(self.results_dir, 'pore_size_distribution.png')),
            ('dist2', 'Межпоровые расстояния', os.path.join(self.results_dir, 'interpore_distances.png')),
            ('rose', 'Роза направлений пор', os.path.join(self.results_dir, 'pore_orientation_rose.png')),
            ('hist', 'Гистограмма ориентации пор', os.path.join(self.results_dir, 'pore_orientation_histogram.png')),
            ('shapes', 'Анализ форм пор', os.path.join(self.results_dir, 'pore_shapes_analysis.png')),
            ('circ', 'Распределение кругового фактора', os.path.join(self.results_dir, 'circularity_distribution.png')),
            ('ellipt', 'Зависимость эллиптичности от площади', os.path.join(self.results_dir, 'ellipticity_vs_area.png'))
        ]
        
        for key, description, image_path in images_to_check:
            # Проверяем только те изображения, которых нет в памяти
            if key not in found_keys:
                logger.debug(f"Проверяем fallback для {key}: {image_path}")
                if os.path.exists(image_path) and os.path.isfile(image_path):
                    if os.path.getsize(image_path) > 0:
                        try:
                            pil_img = Image.open(image_path)
                            available_images.append((pil_img, description, key))
                            logger.debug(f"Добавлено изображение {key} с диска")
                        except Exception as e:
                            logger.warning(f"Ошибка при загрузке изображения {key} с диска: {e}")
                    else:
                        logger.debug(f"Файл {key} пустой: {image_path}")
                else:
                    logger.debug(f"Файл {key} не найден: {image_path}")
        
        logger.info(f"Всего доступных изображений для отчета: {len(available_images)}")
        logger.info(f"Ключи найденных изображений: {[key for _, _, key in available_images]}")
        return available_images
        
    def generate_docx_report(self, output_path: str) -> bool:
        """
        Генерирует отчет в формате .docx
        
        Args:
            output_path: Путь для сохранения файла отчета
            
        Returns:
            bool: True если отчет создан успешно
        """
        try:
            # Создаем документ
            doc = Document()
            
            # Настройка полей страницы (левое 3см, верхнее 2см, нижнее 2см, правое 1.5см)
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(2 / 2.54)      # 2 см в дюймах
                section.bottom_margin = Inches(2 / 2.54)   # 2 см в дюймах
                section.left_margin = Inches(3 / 2.54)     # 3 см в дюймах
                section.right_margin = Inches(1.5 / 2.54)  # 1.5 см в дюймах
                
                # Добавляем номера страниц в нижний колонтитул (кроме первой страницы)
                section.different_first_page_header_footer = True
                footer = section.footer
                footer_para = footer.paragraphs[0]
                
                # Очищаем параграф
                footer_para._element.clear()
                
                # Упрощенный способ добавления номера страницы
                from docx.oxml import parse_xml
                from docx.oxml.ns import nsdecls, qn
                
                # Добавляем XML для номера страницы
                page_num_run = parse_xml(r'<w:r {}><w:fldChar w:fldCharType="begin"/></w:r>'.format(nsdecls('w')))
                footer_para._element.append(page_num_run)
                
                page_num_run2 = parse_xml(r'<w:r {}><w:instrText> PAGE </w:instrText></w:r>'.format(nsdecls('w')))
                footer_para._element.append(page_num_run2)
                
                page_num_run3 = parse_xml(r'<w:r {}><w:fldChar w:fldCharType="end"/></w:r>'.format(nsdecls('w')))
                footer_para._element.append(page_num_run3)
                
                # Устанавливаем центрирование и стиль
                footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Применяем стиль к параграфу
                for run in footer_para.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
            
            # Настройка стилей по умолчанию
            style = doc.styles['Normal']
            font = style.font
            font.name = 'Times New Roman'
            font.size = Pt(14)
            font.color.rgb = RGBColor(0, 0, 0)
            
            # Заголовок
            title = doc.add_heading('Отчет по анализу пористости', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run = title.runs[0]
            title_run.font.name = 'Times New Roman'
            title_run.font.size = Pt(18)
            title_run.font.bold = True
            title_run.font.color.rgb = RGBColor(0, 0, 0)
            
            # Подпись таблицы 1
            table1_caption = doc.add_paragraph()
            table1_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table1_caption_run = table1_caption.add_run("Таблица 1. Общая информация об анализе")
            table1_caption_run.font.name = 'Times New Roman'
            table1_caption_run.font.size = Pt(14)
            table1_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            info_table = doc.add_table(rows=4, cols=2)
            info_table.style = 'Table Grid'
            
            # Используем start_time если доступен, иначе created_at
            analysis_date = self.analysis.start_time if self.analysis.start_time else self.analysis.created_at
            
            info_data = [
                ('Название анализа:', self.analysis.name),
                ('Дата проведения:', analysis_date.strftime('%d.%m.%Y %H:%M')),
                ('Статус:', 'Завершен' if self.analysis.status == 'completed' else self.analysis.status),
                ('Масштаб:', f'{self.analysis.scale_value} мкм')
            ]
            
            for i, (label, value) in enumerate(info_data):
                info_table.cell(i, 0).text = label
                info_table.cell(i, 1).text = str(value)
                # Стилизация первого столбца (убираем жирный)
                cell0_run = info_table.cell(i, 0).paragraphs[0].runs[0]
                cell0_run.font.name = 'Times New Roman'
                cell0_run.font.size = Pt(14)
                cell0_run.font.bold = False
                cell0_run.font.color.rgb = RGBColor(0, 0, 0)
                # Стилизация второго столбца
                cell1_run = info_table.cell(i, 1).paragraphs[0].runs[0]
                cell1_run.font.name = 'Times New Roman'
                cell1_run.font.size = Pt(14)
                cell1_run.font.color.rgb = RGBColor(0, 0, 0)
            
            doc.add_paragraph()
            
            # Результаты анализа
            results_heading = doc.add_heading('Результаты анализа', level=1)
            results_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            results_heading_run = results_heading.runs[0]
            results_heading_run.font.name = 'Times New Roman'
            results_heading_run.font.size = Pt(16)
            results_heading_run.font.bold = True
            results_heading_run.font.color.rgb = RGBColor(0, 0, 0)
            
            # Подпись таблицы 2
            table2_caption = doc.add_paragraph()
            table2_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table2_caption_run = table2_caption.add_run("Таблица 2. Основные показатели анализа")
            table2_caption_run.font.name = 'Times New Roman'
            table2_caption_run.font.size = Pt(14)
            table2_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            main_table = doc.add_table(rows=7, cols=2)
            main_table.style = 'Table Grid'
            
            main_data = [
                ('Процент пористости:', f'{self.analysis.porosity_percentage:.2f}%' if self.analysis.porosity_percentage else 'Н/Д'),
                ('Количество пор:', str(self.analysis.number_of_pores) if self.analysis.number_of_pores else 'Н/Д'),
                ('Средний размер пор:', f'{self.analysis.average_pore_size:.2f} мкм' if self.analysis.average_pore_size else 'Н/Д'),
                ('Максимальный размер пор:', f'{self.analysis.max_pore_size:.2f} мкм' if self.analysis.max_pore_size else 'Н/Д'),
                ('Минимальный размер пор:', f'{self.analysis.min_pore_size:.2f} мкм' if self.analysis.min_pore_size else 'Н/Д'),
                ('Плотность пор:', f'{self.analysis.pore_density:.4f} пор/мкм²' if self.analysis.pore_density else 'Н/Д'),
                ('Среднее межпоровое расстояние:', f'{self.analysis.average_interpore_distance:.2f} мкм' if self.analysis.average_interpore_distance else 'Н/Д')
            ]
            
            for i, (label, value) in enumerate(main_data):
                main_table.cell(i, 0).text = label
                main_table.cell(i, 1).text = value
                # Стилизация первого столбца (убираем жирный)
                main_cell0_run = main_table.cell(i, 0).paragraphs[0].runs[0]
                main_cell0_run.font.name = 'Times New Roman'
                main_cell0_run.font.size = Pt(14)
                main_cell0_run.font.bold = False
                main_cell0_run.font.color.rgb = RGBColor(0, 0, 0)
                # Стилизация второго столбца
                main_cell1_run = main_table.cell(i, 1).paragraphs[0].runs[0]
                main_cell1_run.font.name = 'Times New Roman'
                main_cell1_run.font.size = Pt(14)
                main_cell1_run.font.color.rgb = RGBColor(0, 0, 0)
            
            doc.add_paragraph()
            
            # Получаем данные о группах пор из результатов анализа
            pore_clusters_data = self._get_pore_clusters_data()
            
            # Подпись таблицы 3 - Группы (скопления) пор
            table3_caption = doc.add_paragraph()
            table3_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table3_caption_run = table3_caption.add_run("Таблица 3. Группы (скопления) пор")
            table3_caption_run.font.name = 'Times New Roman'
            table3_caption_run.font.size = Pt(14)
            table3_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            pore_groups_table = doc.add_table(rows=4, cols=4)
            pore_groups_table.style = 'Table Grid'
            
            # Заголовки таблицы групп пор (БЕЗ жирного шрифта)
            headers = ['Параметр', 'Минимальное', 'Максимальное', 'Среднее']
            for j, header in enumerate(headers):
                cell = pore_groups_table.cell(0, j)
                cell.text = header
                cell_run = cell.paragraphs[0].runs[0]
                cell_run.font.name = 'Times New Roman'
                cell_run.font.size = Pt(14)
                cell_run.font.bold = False  # Убираем жирный шрифт
                cell_run.font.color.rgb = RGBColor(0, 0, 0)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Данные таблицы групп пор из реального анализа
            pore_groups_data = [
                ['Площадь, мкм²', 
                 self._format_number(pore_clusters_data["min_area"]), 
                 self._format_number(pore_clusters_data["max_area"]), 
                 self._format_number(pore_clusters_data["mean_area"])],
                ['Мин проекция, мкм', 
                 self._format_number(pore_clusters_data["min_minor_axis"]), 
                 self._format_number(pore_clusters_data["max_minor_axis"]), 
                 self._format_number(pore_clusters_data["mean_minor_axis"])],
                ['Макс проекция, мкм', 
                 self._format_number(pore_clusters_data["min_major_axis"]), 
                 self._format_number(pore_clusters_data["max_major_axis"]), 
                 self._format_number(pore_clusters_data["mean_major_axis"])]
            ]
            
            for i, row_data in enumerate(pore_groups_data, start=1):
                for j, value in enumerate(row_data):
                    cell = pore_groups_table.cell(i, j)
                    cell.text = value
                    cell_run = cell.paragraphs[0].runs[0]
                    cell_run.font.name = 'Times New Roman'
                    cell_run.font.size = Pt(14)
                    cell_run.font.color.rgb = RGBColor(0, 0, 0)
                    if j == 0:  # Первый столбец - по левому краю
                        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                    else:  # Остальные столбцы - по центру
                        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.add_paragraph()
            
            # Получаем данные об анализируемой площади
            analyzed_area_data = self._get_analyzed_area_data()
            
            # Подпись таблицы 4 - Распределение пор по размерам
            table4_caption = doc.add_paragraph()
            table4_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table4_caption_run = table4_caption.add_run("Таблица 4. Распределение пор по размерам")
            table4_caption_run.font.name = 'Times New Roman'
            table4_caption_run.font.size = Pt(14)
            table4_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            pore_distribution_table = doc.add_table(rows=1, cols=2)
            pore_distribution_table.style = 'Table Grid'
            
            # Данные таблицы распределения
            pore_distribution_table.cell(0, 0).text = 'Проанализированная площадь, мм²'
            pore_distribution_table.cell(0, 1).text = f'{analyzed_area_data["area_mm2"]:.6f}'
            
            # Стилизация таблицы распределения
            for i in range(1):
                for j in range(2):
                    cell_run = pore_distribution_table.cell(i, j).paragraphs[0].runs[0]
                    cell_run.font.name = 'Times New Roman'
                    cell_run.font.size = Pt(14)
                    cell_run.font.color.rgb = RGBColor(0, 0, 0)
            
            doc.add_paragraph()
            
            # Получаем данные о размерах пор и общую статистику
            detailed_analysis_data = self._get_detailed_analysis_data()
            
            # Подпись таблицы 5 - Таблица распределения пор по размерам
            table5_caption = doc.add_paragraph()
            table5_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table5_caption_run = table5_caption.add_run("Таблица 5. Таблица распределения пор по размерам")
            table5_caption_run.font.name = 'Times New Roman'
            table5_caption_run.font.size = Pt(14)
            table5_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            # Сначала общие показатели
            general_info_table = doc.add_table(rows=4, cols=2)
            general_info_table.style = 'Table Grid'
            
            general_info_data = [
                ('Площадь анализа, мкм²', f'{analyzed_area_data["area_microns2"]:.0f}'),
                ('Общее количество объектов', f'{detailed_analysis_data["total_objects"]}'),
                ('Суммарная площадь объектов, мкм²', f'{detailed_analysis_data["total_pore_area"]:.0f}'),
                ('Доля по площади, %', f'{detailed_analysis_data["area_fraction"]:.2f}')
            ]
            
            for i, (label, value) in enumerate(general_info_data):
                general_info_table.cell(i, 0).text = label
                general_info_table.cell(i, 1).text = str(value)
                # Стилизация
                cell0_run = general_info_table.cell(i, 0).paragraphs[0].runs[0]
                cell0_run.font.name = 'Times New Roman'
                cell0_run.font.size = Pt(14)
                cell0_run.font.bold = False
                cell0_run.font.color.rgb = RGBColor(0, 0, 0)
                cell1_run = general_info_table.cell(i, 1).paragraphs[0].runs[0]
                cell1_run.font.name = 'Times New Roman'
                cell1_run.font.size = Pt(14)
                cell1_run.font.color.rgb = RGBColor(0, 0, 0)
            
            doc.add_paragraph()
            
            # Подпись таблицы 6 - Диаметр эквивалентного круга
            table6_caption = doc.add_paragraph()
            table6_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table6_caption_run = table6_caption.add_run("Таблица 6. Диаметр экв.круга внешнего контура")
            table6_caption_run.font.name = 'Times New Roman'
            table6_caption_run.font.size = Pt(14)
            table6_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            # Отдельная таблица для диаметра эквивалентного круга
            diameter_stats_table = doc.add_table(rows=5, cols=2)
            diameter_stats_table.style = 'Table Grid'
            
            diameter_stats_data = [
                ('Минимальная величина, мкм', self._format_number(detailed_analysis_data["min_diameter"])),
                ('Максимальная величина, мкм', self._format_number(detailed_analysis_data["max_diameter"])),
                ('Средняя величина, мкм', self._format_number(detailed_analysis_data["mean_diameter"])),
                ('СКО, мкм', self._format_number(detailed_analysis_data["std_diameter"])),
                ('Медианная величина, мкм', self._format_number(detailed_analysis_data["median_diameter"]))
            ]
            
            for i, (label, value) in enumerate(diameter_stats_data):
                diameter_stats_table.cell(i, 0).text = label
                diameter_stats_table.cell(i, 1).text = str(value)
                # Стилизация
                cell0_run = diameter_stats_table.cell(i, 0).paragraphs[0].runs[0]
                cell0_run.font.name = 'Times New Roman'
                cell0_run.font.size = Pt(14)
                cell0_run.font.bold = False
                cell0_run.font.color.rgb = RGBColor(0, 0, 0)
                cell1_run = diameter_stats_table.cell(i, 1).paragraphs[0].runs[0]
                cell1_run.font.name = 'Times New Roman'
                cell1_run.font.size = Pt(14)
                cell1_run.font.color.rgb = RGBColor(0, 0, 0)
            
            doc.add_paragraph()
            
            # Подпись таблицы 7 - Детальная таблица распределения
            table7_caption = doc.add_paragraph()
            table7_caption.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            table7_caption_run = table7_caption.add_run("Таблица 7. Детальная таблица распределения пор по размерам")
            table7_caption_run.font.name = 'Times New Roman'
            table7_caption_run.font.size = Pt(14)
            table7_caption_run.font.color.rgb = RGBColor(0, 0, 0)
            
            # Детальная таблица распределения по размерам
            size_distribution = detailed_analysis_data["size_distribution"]
            
            # Создаем таблицу с реальными данными
            num_bins = len(size_distribution)
            detailed_distribution_table = doc.add_table(rows=num_bins + 1, cols=7)
            detailed_distribution_table.style = 'Table Grid'
            
            # Заголовки детальной таблицы (БЕЗ жирного шрифта)
            detailed_headers = [
                'Размер,\nмкм', 'Кол-во', 'Доля\nпо кол-ву\n%', 
                'Суммарная\nплощадь,\nмкм²', 'Доля\nпо площади\n%', 
                'Суммарный\nобъём,\nмкм³', 'Доля\nпо объему\n%'
            ]
            
            for j, header in enumerate(detailed_headers):
                cell = detailed_distribution_table.cell(0, j)
                cell.text = header
                cell_run = cell.paragraphs[0].runs[0]
                cell_run.font.name = 'Times New Roman'
                cell_run.font.size = Pt(14)
                cell_run.font.bold = False  # Убираем жирный шрифт
                cell_run.font.color.rgb = RGBColor(0, 0, 0)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Данные детальной таблицы из реального анализа
            for i, (_, row) in enumerate(size_distribution.iterrows(), start=1):
                row_data = [
                    row['Интервал диаметров (мкм)'],
                    str(row['Количество пор']),
                    self._format_number(row['Доля по количеству (%)']),
                    self._format_number(row['Общая площадь (мкм²)']),
                    self._format_number(row['Доля по площади (%)']),
                    self._format_number(row['Общий объем (мкм³)']),
                    self._format_number(row['Доля по объему (%)'])
                ]
                
                for j, value in enumerate(row_data):
                    cell = detailed_distribution_table.cell(i, j)
                    cell.text = value
                    cell_run = cell.paragraphs[0].runs[0]
                    cell_run.font.name = 'Times New Roman'
                    cell_run.font.size = Pt(14)
                    cell_run.font.color.rgb = RGBColor(0, 0, 0)
                    if j == 0:  # Первый столбец - по левому краю
                        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                    else:  # Остальные столбцы - по центру
                        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Добавляем изображения
            doc.add_page_break()
            viz_heading = doc.add_heading('Результаты визуализации', level=1)
            viz_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            viz_heading_run = viz_heading.runs[0]
            viz_heading_run.font.name = 'Times New Roman'
            viz_heading_run.font.size = Pt(16)
            viz_heading_run.font.bold = True
            viz_heading_run.font.color.rgb = RGBColor(0, 0, 0)
            
            # Получаем список доступных изображений
            available_images = self._get_available_images()
            descriptions = self._get_image_descriptions()
            
            if not available_images:
                doc.add_paragraph('Изображения результатов анализа не найдены.')
            else:
                fig_num = 1
                for img_or_path, description, key in available_images:
                    logger.debug(f"Обрабатываем изображение для DOCX: {key}")
                    try:
                        # Добавляем изображение с ограничением размера
                        if isinstance(img_or_path, Image.Image):
                            bio = self._compress_image_for_docx(img_or_path, target_width_inches=Inches(5.5).inches, target_dpi=220)
                            pic_paragraph = doc.add_paragraph()
                            pic_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            run = pic_paragraph.add_run()
                            run.add_picture(bio, width=Inches(5.5))
                        else:
                            # Если вдруг попался путь/байты - пробуем через PIL и сжимаем
                            try:
                                pil_img = Image.open(img_or_path) if isinstance(img_or_path, str) else Image.open(BytesIO(img_or_path))
                                bio = self._compress_image_for_docx(pil_img, target_width_inches=Inches(5.5).inches, target_dpi=220)
                                pic_paragraph = doc.add_paragraph()
                                pic_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                run = pic_paragraph.add_run()
                                run.add_picture(bio, width=Inches(5.5))
                            except Exception:
                                pic_paragraph = doc.add_paragraph()
                                pic_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                run = pic_paragraph.add_run()
                                run.add_picture(img_or_path, width=Inches(5.5))
                        
                        # Добавляем подпись под изображением
                        caption_para = doc.add_paragraph()
                        caption_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # Заголовок рисунка
                        title = descriptions.get(key, {}).get('title', description)
                        caption_run = caption_para.add_run(f"Рис. {fig_num}. {title}")
                        caption_run.font.name = 'Times New Roman'
                        caption_run.font.size = Pt(14)
                        caption_run.font.bold = True
                        caption_run.font.color.rgb = RGBColor(0, 0, 0)
                        
                        # Описание с метриками
                        desc_text = descriptions.get(key, {}).get('description', '')
                        if desc_text:
                            desc_para = doc.add_paragraph(desc_text)
                            desc_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                            # Добавляем отступ первой строки 1.25 см
                            desc_para.paragraph_format.first_line_indent = Inches(1.25 / 2.54)  # Конвертируем см в дюймы
                            for run in desc_para.runs:
                                run.font.name = 'Times New Roman'
                                run.font.size = Pt(14)
                                run.font.color.rgb = RGBColor(0, 0, 0)
                        
                        doc.add_paragraph()  # Отступ между изображениями
                        fig_num += 1
                        
                    except Exception as e:
                        logger.warning(f"Не удалось добавить изображение {key}: {e}")
                        doc.add_paragraph(f"[Изображение {description} недоступно]")
            
            # Сохраняем документ
            doc.save(output_path)
            logger.info(f"Отчет DOCX сохранен: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при генерации DOCX отчета: {e}")
            return False
    
    def convert_docx_to_pdf(self, docx_path: str, pdf_path: str) -> bool:
        """
        Конвертирует DOCX файл в PDF используя кроссплатформенные инструменты
        
        Args:
            docx_path: Путь к DOCX файлу
            pdf_path: Путь для сохранения PDF файла
            
        Returns:
            bool: True если конвертация прошла успешно
        """
        try:
            if not os.path.exists(docx_path):
                logger.error(f"DOCX файл не найден: {docx_path}")
                return False
            
            # Проверяем доступные инструменты конвертации
            available_tools = [tool for tool, available in CONVERSION_TOOLS.items() if available]
            
            if not available_tools:
                logger.warning("Не найдены инструменты для конвертации DOCX в PDF (LibreOffice, unoconv)")
                return False
            
            # Получаем директорию для вывода
            output_dir = os.path.dirname(pdf_path)
            pdf_filename = os.path.basename(pdf_path)
            
            success = False
            
            # Пробуем unoconv (самый надежный)
            if 'unoconv' in available_tools:
                try:
                    cmd = [
                        'unoconv', 
                        '-f', 'pdf', 
                        '-o', pdf_path,
                        docx_path
                    ]
                    logger.debug(f"Запускаем команду unoconv: {' '.join(cmd)}")
                    
                    # Используем более короткий таймаут и проверяем процесс
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        stdout, stderr = process.communicate(timeout=30)
                        returncode = process.returncode
                        
                        if returncode == 0 and os.path.exists(pdf_path):
                            logger.info(f"PDF создан с помощью unoconv: {pdf_path}")
                            success = True
                        else:
                            logger.warning(f"unoconv завершился с кодом {returncode}, ошибка: {stderr}")
                            
                    except subprocess.TimeoutExpired:
                        logger.warning("unoconv превысил время ожидания, принудительно завершаем процесс")
                        process.kill()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            logger.error("Не удалось корректно завершить процесс unoconv")
                        
                except Exception as e:
                    logger.warning(f"Ошибка при работе с unoconv: {e}")
            
            # Если unoconv не сработал, пробуем LibreOffice с уникальным профилем, локами и ретраями
            if not success and ('libreoffice' in available_tools or 'soffice' in available_tools):
                # Глобальная блокировка для сериализации конвертаций LibreOffice (временная директория ОС)
                lock_path = str(Path(tempfile.gettempdir()) / "lo_convert.lock")
                try:
                    Path(lock_path).touch(exist_ok=True)
                except Exception:
                    pass

                max_retries = 3
                base_timeout = 60  # базовый таймаут (увеличивается с каждой попыткой)
                wait_pdf_secs = 5  # ожидание стабилизации PDF

                def _convert_with_lock():
                    nonlocal success
                    with open(lock_path, "w") as lockf:
                        _acquire_file_lock(lockf)

                        for attempt in range(1, max_retries + 1):
                            profile_dir = Path(tempfile.gettempdir()) / f"lo_profile_{uuid.uuid4().hex}"
                            profile_url = f"file://{profile_dir}"
                            soffice_cmd = 'libreoffice' if 'libreoffice' in available_tools else 'soffice'
                            try:
                                profile_dir.mkdir(parents=True, exist_ok=True)

                                cmd = [
                                    soffice_cmd,
                                    '--headless',
                                    '--invisible',
                                    '--nodefault',
                                    '--nolockcheck',
                                    '--nologo',
                                    '--norestore',
                                    f'-env:UserInstallation={profile_url}',
                                    '--convert-to', 'pdf:writer_pdf_Export',
                                    '--outdir', output_dir,
                                    docx_path
                                ]

                                logger.debug(f"Запускаем команду LibreOffice (попытка {attempt}): {' '.join(cmd)}")

                                env = os.environ.copy()
                                env['HOME'] = '/tmp'
                                env['TMPDIR'] = '/tmp'

                                process = subprocess.Popen(
                                    cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    env=env,
                                    preexec_fn=os.setsid
                                )

                                timeout = base_timeout * attempt  # 60, 120, 180
                                try:
                                    stdout, stderr = process.communicate(timeout=timeout)
                                except subprocess.TimeoutExpired:
                                    logger.warning("LibreOffice превысил время ожидания, принудительно завершаем процесс")
                                    try:
                                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                                        process.wait(timeout=5)
                                    except Exception:
                                        try:
                                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                                        except Exception:
                                            pass
                                    stdout, stderr = "", "timeout"

                                returncode = process.returncode

                                # LibreOffice создает PDF с именем исходного файла
                                docx_basename = os.path.splitext(os.path.basename(docx_path))[0]
                                generated_pdf = os.path.join(output_dir, f"{docx_basename}.pdf")

                                if returncode == 0 and os.path.exists(generated_pdf):
                                    # Ждем стабилизации размера PDF
                                    prev_size = -1
                                    stable = False
                                    for _ in range(wait_pdf_secs):
                                        try:
                                            size = os.path.getsize(generated_pdf)
                                        except OSError:
                                            size = -1
                                        if size > 0 and size == prev_size:
                                            stable = True
                                            break
                                        prev_size = size
                                        time.sleep(1)

                                    if stable:
                                        if generated_pdf != pdf_path:
                                            shutil.move(generated_pdf, pdf_path)
                                        logger.info(f"PDF создан с помощью {soffice_cmd}: {pdf_path}")
                                        success = True
                                        break
                                    else:
                                        logger.warning("PDF файл не стабилен по размеру, повторяем попытку")
                                else:
                                    err_tail = (stderr or "").strip() if isinstance(stderr, str) else ""
                                    logger.warning(f"{soffice_cmd} завершился с кодом {returncode}, ошибка: {err_tail}")

                                # Бэкофф перед следующей попыткой
                                time.sleep(2 * attempt)

                            except Exception as e:
                                logger.warning(f"Ошибка при работе с {soffice_cmd} (попытка {attempt}): {e}")
                            finally:
                                # Чистка временного профиля
                                try:
                                    shutil.rmtree(profile_dir, ignore_errors=True)
                                except Exception:
                                    pass

                        _release_file_lock(lockf)

                _convert_with_lock()
            
            if success and os.path.exists(pdf_path):
                logger.info(f"PDF отчет успешно создан: {pdf_path}")
                return True
            else:
                logger.error(f"Не удалось создать PDF файл: {pdf_path}")
                return False
                
        except Exception as e:
            logger.error(f"Общая ошибка при конвертации DOCX в PDF: {e}")
            return False
    
    def generate_reports(self) -> Dict[str, str]:
        """
        Генерирует отчеты в форматах DOCX и PDF
        
        Returns:
            dict: Словарь с путями к созданным файлам отчетов
        """
        reports = {}
        # Формируем безопасное имя файла на основе названия анализа
        base_photo_name = (self.analysis.name or '').strip() or f"analysis_{self.analysis.id}"
        safe_name = re.sub(r'[^\w\s\-а-яё]', '', base_photo_name, flags=re.IGNORECASE).strip() or f"analysis_{self.analysis.id}"
        
        # Создаем директорию для отчетов если её нет
        reports_dir = os.path.join(self.results_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Генерируем DOCX отчет с именем, соответствующим названию анализа
        docx_path = os.path.join(reports_dir, f'{safe_name}.docx')
        if self.generate_docx_report(docx_path):
            reports['docx'] = docx_path
            logger.info(f"DOCX отчет создан: {docx_path}")
            
            # Конвертируем DOCX в PDF с дополнительной защитой от зависания
            pdf_path = os.path.join(reports_dir, f'{safe_name}.pdf')
            try:
                # Пытаемся создать PDF, но не блокируемся на долго
                if self.convert_docx_to_pdf(docx_path, pdf_path):
                    reports['pdf'] = pdf_path
                    logger.info(f"PDF отчет создан конвертацией из DOCX: {pdf_path}")
                else:
                    logger.warning(f"Не удалось конвертировать DOCX в PDF: {pdf_path}")
            except Exception as pdf_error:
                logger.error(f"Ошибка при создании PDF отчета: {pdf_error}")
                # Продолжаем работу, так как DOCX уже создан
        else:
            logger.error(f"Не удалось создать DOCX отчет: {docx_path}")
        
        return reports
    
    def generate_single_report(self, report_type: str) -> Optional[str]:
        """
        Генерирует отчет только указанного типа
        
        Args:
            report_type: Тип отчета ('docx' или 'pdf')
            
        Returns:
            str: Путь к созданному файлу отчета или None при ошибке
        """
        if report_type not in ['docx', 'pdf']:
            logger.error(f"Неподдерживаемый тип отчета: {report_type}")
            return None
            
        # Формируем безопасное имя файла на основе названия анализа
        base_photo_name = (self.analysis.name or '').strip() or f"analysis_{self.analysis.id}"
        safe_name = re.sub(r'[^\w\s\-а-яё]', '', base_photo_name, flags=re.IGNORECASE).strip() or f"analysis_{self.analysis.id}"
        
        # Создаем директорию для отчетов если её нет
        reports_dir = os.path.join(self.results_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        if report_type == 'docx':
            # Генерируем только DOCX
            docx_path = os.path.join(reports_dir, f'{safe_name}.docx')
            if self.generate_docx_report(docx_path):
                logger.info(f"DOCX отчет создан: {docx_path}")
                return docx_path
            else:
                logger.error(f"Не удалось создать DOCX отчет: {docx_path}")
                return None
                
        elif report_type == 'pdf':
            # Сначала создаем DOCX, затем конвертируем в PDF
            docx_path = os.path.join(reports_dir, f'{safe_name}.docx')
            pdf_path = os.path.join(reports_dir, f'{safe_name}.pdf')
            
            if self.generate_docx_report(docx_path):
                if self.convert_docx_to_pdf(docx_path, pdf_path):
                    logger.info(f"PDF отчет создан: {pdf_path}")
                    # Удаляем временный DOCX файл
                    try:
                        os.remove(docx_path)
                    except Exception:
                        pass
                    return pdf_path
                else:
                    logger.error(f"Не удалось конвертировать DOCX в PDF: {pdf_path}")
                    return None
            else:
                logger.error(f"Не удалось создать DOCX для конвертации в PDF")
                return None
        
        return None