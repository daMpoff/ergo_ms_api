import os
import logging
import subprocess
import shutil
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
                'description': f'Слева: исходное изображение в оттенках серого. Справа: изображение после адаптивного улучшения контраста методом CLAHE (Contrast Limited Adaptive Histogram Equalization) с размером сетки 8x8 пикселей и ограничением контраста 2.0 для лучшего выделения пор. Затем применяется билатеральная фильтрация для шумоподавления с сохранением краев.'
            },
            'figure2': {    
                'title': 'Исключенные области',
                'description': f'Визуализация областей, исключенных из анализа. Исключено линий: {lines_excluded} пикселей, аномалий: {anomalies_excluded} пикселей. Общий процент исключенных областей: {excluded_percent:.1f}%.'
            },
            'figure3': {
                'title': 'Текстурный анализ',
                'description': f'Слева: карта локальной энтропии для анализа текстуры с окном размером 3 пикселя. Справа: результат K-means кластеризации (K=3 кластера) для сегментации изображения на фон, материал и поры. Кластеризация выполняется по признакам интенсивности пикселей и локальной энтропии для повышения точности сегментации.'
            },
            'figure4': {
                'title': 'Бинарная маска и результат анализа',
                'description': f'Слева: бинарная маска обнаруженных пор после морфологического открытия с диском радиусом 3 пикселя и удаления объектов менее 5 пикселей. Справа: маркированные поры после применения алгоритма водораздела для разделения слипшихся пор. Обнаружено пор: {num_pores}. Площадь всех пор составляет {(num_pores * mean_size if num_pores > 0 else 0):.1f} мкм².'
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
            
            info_data = [
                ('Название анализа:', self.analysis.name),
                ('Дата проведения:', self.analysis.created_at.strftime('%d.%m.%Y %H:%M')),
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
                            bio = BytesIO()
                            img_or_path.save(bio, format='PNG')
                            bio.seek(0)
                            pic_paragraph = doc.add_paragraph()
                            pic_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            run = pic_paragraph.add_run()
                            run.add_picture(bio, width=Inches(5.5))
                        else:
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
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and os.path.exists(pdf_path):
                        logger.info(f"PDF создан с помощью unoconv: {pdf_path}")
                        success = True
                    else:
                        logger.warning(f"unoconv завершился с ошибкой: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.warning("unoconv превысил время ожидания")
                except Exception as e:
                    logger.warning(f"Ошибка при работе с unoconv: {e}")
            
            # Если unoconv не сработал, пробуем LibreOffice
            if not success and ('libreoffice' in available_tools or 'soffice' in available_tools):
                try:
                    # Выбираем команду
                    soffice_cmd = 'libreoffice' if 'libreoffice' in available_tools else 'soffice'
                    
                    cmd = [
                        soffice_cmd,
                        '--headless',
                        '--convert-to', 'pdf',
                        '--outdir', output_dir,
                        docx_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    # LibreOffice создает PDF с именем исходного файла
                    docx_basename = os.path.splitext(os.path.basename(docx_path))[0]
                    generated_pdf = os.path.join(output_dir, f"{docx_basename}.pdf")
                    
                    if result.returncode == 0 and os.path.exists(generated_pdf):
                        # Переименовываем в нужное имя если необходимо
                        if generated_pdf != pdf_path:
                            shutil.move(generated_pdf, pdf_path)
                        
                        logger.info(f"PDF создан с помощью {soffice_cmd}: {pdf_path}")
                        success = True
                    else:
                        logger.warning(f"{soffice_cmd} завершился с ошибкой: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"{soffice_cmd} превысил время ожидания")
                except Exception as e:
                    logger.warning(f"Ошибка при работе с {soffice_cmd}: {e}")
            
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
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Создаем директорию для отчетов если её нет
        reports_dir = os.path.join(self.results_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Генерируем DOCX отчет
        docx_path = os.path.join(reports_dir, f'porosity_report_{timestamp}.docx')
        if self.generate_docx_report(docx_path):
            reports['docx'] = docx_path
            logger.info(f"DOCX отчет создан: {docx_path}")
            
            # Конвертируем DOCX в PDF
            pdf_path = os.path.join(reports_dir, f'porosity_report_{timestamp}.pdf')
            if self.convert_docx_to_pdf(docx_path, pdf_path):
                reports['pdf'] = pdf_path
                logger.info(f"PDF отчет создан конвертацией из DOCX: {pdf_path}")
            else:
                logger.warning(f"Не удалось конвертировать DOCX в PDF: {pdf_path}")
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
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Создаем директорию для отчетов если её нет
        reports_dir = os.path.join(self.results_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        if report_type == 'docx':
            # Генерируем только DOCX
            docx_path = os.path.join(reports_dir, f'porosity_report_{timestamp}.docx')
            if self.generate_docx_report(docx_path):
                logger.info(f"DOCX отчет создан: {docx_path}")
                return docx_path
            else:
                logger.error(f"Не удалось создать DOCX отчет: {docx_path}")
                return None
                
        elif report_type == 'pdf':
            # Сначала создаем DOCX, затем конвертируем в PDF
            docx_path = os.path.join(reports_dir, f'porosity_report_{timestamp}.docx')
            pdf_path = os.path.join(reports_dir, f'porosity_report_{timestamp}.pdf')
            
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