"""
Модуль для создания Word протоколов анализа импульсов.
Содержит функции для генерации документов с результатами анализа.
"""

import os
import math
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

from django.conf import settings
from src.core.utils.database.dbconfig import DBConfig
from src.core.utils.database.base import SqlAlchemyManager
from src.modules.impuls_analysis.models import ImpulsProtocol

logger = logging.getLogger('impuls_analysis')


def format_sig_plain(x: float, sig: int = 2, decimal_comma: bool = False) -> str:
    """
    Форматирует число с заданным количеством значащих цифр
    
    Args:
        x: Число для форматирования
        sig: Количество значащих цифр
        decimal_comma: Использовать запятую вместо точки
        
    Returns:
        Отформатированная строка
    """
    if x == 0 or not math.isfinite(x):
        s = "0" if x == 0 else str(x)
    else:
        exp = math.floor(math.log10(abs(x)))     # порядок
        scale = sig - 1 - exp                    # сколько знаков после точки нужно
        if scale >= 0:
            s = f"{x:.{scale}f}"                 # фикс. кол-во десятичных знаков
        else:
            s = f"{round(x, scale):.0f}"         # округление до десятков/сотен и т.п.
    return s.replace('.', ',') if decimal_comma else s


def get_analysis_by_protocol_number(protocol_number: str) -> dict:
    """
    Получает всю информацию об анализе по номеру протокола
    
    Args:
        protocol_number (str): Номер протокола
        
    Returns:
        dict: Словарь с DataFrame'ами всех связанных данных
    """
    
    # Инициализация подключения к базе данных
    with DBConfig() as db_config:
        db_manager = SqlAlchemyManager(db_config)
        
        try:
            # 1. Основная информация об анализе
            analysis_query = """
                SELECT 
                    ia.id,
                    ia.title,
                    ia.description,
                    ia.protocol_number,
                    ia.status,
                    ia.created_at,
                    ia.updated_at,
                    ia.started_at,
                    ia.completed_at,
                    ia.p_static,
                    ia.energy_j,
                    ia.error_message,
                    ia.task_id,
                    u.username as user_username,
                    u.email as user_email
                FROM impuls_analysis_impulsanalysis ia
                LEFT JOIN auth_user u ON ia.user_id = u.id
                WHERE ia.protocol_number = %(protocol_number)s::text
            """
            
            analysis_df = db_manager.fetchall(
                lambda: (analysis_query, {'protocol_number': protocol_number})
            )
            
            if analysis_df.empty:
                return {"error": f"Анализ с номером протокола '{protocol_number}' не найден"}
            
            analysis_id = analysis_df.iloc[0]['id']
            
            # 2. Файлы анализа
            files_query = """
                SELECT 
                    if.id,
                    if.file_type,
                    if.file,
                    if.original_filename,
                    if.file_size,
                    if.uploaded_at
                FROM impuls_analysis_impulsfile if
                WHERE if.analysis_id = %(analysis_id)s
            """
            
            files_df = db_manager.fetchall(
                lambda: (files_query, {'analysis_id': analysis_id})
            )
            
            # 3. Протоколы анализа
            protocols_query = """
                SELECT 
                    ip.id,
                    ip.protocol_file,
                    ip.generated_at,
                    ip.file_size
                FROM impuls_analysis_impulsprotocol ip
                WHERE ip.analysis_id = %(analysis_id)s
                ORDER BY ip.generated_at DESC
            """
            
            protocols_df = db_manager.fetchall(
                lambda: (protocols_query, {'analysis_id': analysis_id})
            )
            
            # 4. Записи расчета силы
            force_records_query = """
                SELECT 
                    ifr.id,
                    ifr.sheet_title,
                    ifr.protocol_number,
                    ifr.pct_static,
                    ifr.v,
                    ifr.p,
                    ifr.f,
                    ifr.energy_j,
                    ifr.velocity_ms,
                    ifr.force_n,
                    ifr.created_at
                FROM impuls_analysis_impulsforcerecord ifr
                WHERE ifr.protocol_number = %(protocol_number)s::text
                ORDER BY ifr.created_at DESC
            """
            
            force_records_df = db_manager.fetchall(
                lambda: (force_records_query, {'protocol_number': protocol_number})
            )
            
            # 5. Записи плана эксперимента
            plan_records_query = """
                SELECT 
                    ipr.id,
                    ipr.protocol_number,
                    ipr.p_static,
                    ipr.p_static_value,
                    ipr.l1_l2_ratio,
                    ipr.l1_m,
                    ipr.d1_m,
                    ipr.m1_kg,
                    ipr.l2_m,
                    ipr.d2_m,
                    ipr.t_s,
                    ipr.a_j,
                    ipr.v_ms,
                    ipr.c12_kg_s,
                    ipr.p_n,
                    ipr.created_at
                FROM impuls_analysis_impulsplanrecord ipr
                WHERE ipr.protocol_number = %(protocol_number)s::text
                ORDER BY ipr.created_at DESC
            """
            
            plan_records_df = db_manager.fetchall(
                lambda: (plan_records_query, {'protocol_number': protocol_number})
            )
            
            # 6. Экстремумы импульсов
            extrema_query = """
                SELECT 
                    ie.id,
                    ie.pulse_id,
                    ie.extremum_id,
                    ie.extremum_type,
                    ie.v,
                    ie.f,
                    ie.duration_v,
                    ie.area,
                    ie.v_start,
                    ie.v_end,
                    ie.created_at
                FROM impuls_analysis_impulsextremum ie
                WHERE ie.analysis_id = %(analysis_id)s
                ORDER BY ie.pulse_id, ie.extremum_id
            """
            
            extrema_df = db_manager.fetchall(
                lambda: (extrema_query, {'analysis_id': analysis_id})
            )
            
            # Формируем результат
            result = {
                "analysis": analysis_df,
                "files": files_df,
                "protocols": protocols_df,
                "force_records": force_records_df,
                "plan_records": plan_records_df,
                "extrema": extrema_df,
                "summary": {
                    "protocol_number": protocol_number,
                    "analysis_id": analysis_id,
                    "total_files": len(files_df),
                    "total_protocols": len(protocols_df),
                    "total_force_records": len(force_records_df),
                    "total_plan_records": len(plan_records_df),
                    "total_extrema": len(extrema_df)
                }
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Ошибка при получении данных: {str(e)}"}
        
        finally:
            db_manager.close()


def create_impulse_tables(doc, extrema_df):
    """
    Создает таблицы с параметрами импульсов
    
    Args:
        doc: Document объект
        extrema_df: DataFrame с данными экстремумов
    """
    if extrema_df.empty:
        return
        
    grouped = extrema_df.groupby('pulse_id')

    for pulse_id, group in grouped:
        # Заголовок импульса
        impulse_header = doc.add_paragraph()
        impulse_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        impulse_header.paragraph_format.space_after = Pt(6)
        
        header_run = impulse_header.add_run(f"Импульс S{pulse_id}")
        header_run.font.name = 'Times New Roman'
        header_run.font.size = Pt(14)
        header_run.bold = True

        num_extrema = len(group)

        # Всего строк = 1 (заголовки) + num_extrema (макс. сила) + 2 (длительность, площадь)
        table_rows = 1 + num_extrema + 2
        table = doc.add_table(rows=table_rows, cols=3)
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Заголовки
        header_cells = table.rows[0].cells
        header_cells[0].text = 'Параметр'
        header_cells[1].text = 'Мера измерения'
        header_cells[2].text = 'Значение'

        # Форматирование заголовков таблицы (жирный шрифт)
        for cell in header_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(14)
                    run.bold = True

        # --- Блок "Максимальное значение силы в точке" ---
        start_row = 1
        end_row = start_row + num_extrema - 1

        # Объединяем ячейки первой колонки
        a = table.cell(start_row, 0)
        b = table.cell(end_row, 0)
        a.merge(b)
        a.text = "Максимальное значение силы в точке"

        # Заполняем 2 и 3 колонки
        for i in range(num_extrema):
            row = table.rows[start_row + i]
            
            # Создаем текст с нижним индексом для F{i+1}
            cell_1 = row.cells[1]
            cell_1.text = ""  # Очищаем ячейку
            paragraph = cell_1.paragraphs[0]
            
            # Добавляем "F" обычным шрифтом
            run1 = paragraph.add_run("F")
            run1.font.name = 'Times New Roman'
            run1.font.size = Pt(14)
            
            # Добавляем число как нижний индекс
            run2 = paragraph.add_run(str(i+1))
            run2.font.name = 'Times New Roman'
            run2.font.size = Pt(14)
            run2.font.subscript = True
            
            # Добавляем ", H"
            run3 = paragraph.add_run(", H")
            run3.font.name = 'Times New Roman'
            run3.font.size = Pt(14)
            
            row.cells[2].text = f"{group['f'].iloc[i]:.2f}"  # сюда можно подставить значение силы

        # --- Длительность импульса ---
        duration_row = table.rows[end_row + 1]
        duration_row.cells[0].text = "Длительность импульса"
        duration_row.cells[1].text = "T, сек"
        duration = float(group['duration_v'].iloc[0])
        duration_row.cells[2].text = format_sig_plain(duration, 2, decimal_comma=True)

        # --- Площадь импульса ---
        area_row = table.rows[end_row + 2]
        area_row.cells[0].text = "Площадь импульса"
        area_row.cells[1].text = "S, H/с²"
        area_row.cells[2].text = f"{float(group['area'].iloc[0]):.2f}"

        # Форматирование всех ячеек таблицы (Times New Roman 14)
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(14)

        # Добавляем отступ после таблицы
        doc.add_paragraph().paragraph_format.space_after = Pt(12)


def create_force_records_table(doc, force_records_df):
    """
    Создает таблицу с записями расчета силы
    
    Args:
        doc: Document объект
        force_records_df: DataFrame с данными force_records
    """
    if force_records_df.empty:
        return
    
    # Создаем таблицу
    num_rows = len(force_records_df) + 1  # +1 для заголовков
    table = doc.add_table(rows=num_rows, cols=4)
    table.style = 'Table Grid'
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Заголовки таблицы
    header_cells = table.rows[0].cells
    header_cells[0].text = '№'
    header_cells[1].text = 'Время, с'
    header_cells[2].text = 'Сила удара, Н (Р)'
    
    # Создаем заголовок с нижним индексом для "F=10kHz"
    cell_3 = header_cells[3]
    cell_3.text = ""  # Очищаем ячейку
    paragraph = cell_3.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Выравнивание по центру
    
    # Добавляем "Сила удара, Н (фильтр Butterworth 10000Hz) (F="
    run1 = paragraph.add_run("Сила удара, Н (фильтр Butterworth 10000Hz) (F=")
    run1.font.name = 'Times New Roman'
    run1.font.size = Pt(14)
    run1.bold = True
    
    # Добавляем "kHz)"
    run3 = paragraph.add_run("10kHz)")
    run3.font.name = 'Times New Roman'
    run3.font.size = Pt(14)
    run3.bold = True
    
    # Форматирование заголовков таблицы (жирный шрифт и выравнивание по центру)
    for i, cell in enumerate(header_cells):
        if i != 3:  # 3-я ячейка уже отформатирована выше
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Выравнивание по центру
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(14)
                    run.bold = True
    
    # Заполняем данные
    for idx, (_, row) in enumerate(force_records_df.iterrows(), 1):
        data_row = table.rows[idx]
        data_row.cells[0].text = str(idx)  # №
        data_row.cells[1].text = format_sig_plain(row['v'], 2, decimal_comma=True)  # Время, с
        data_row.cells[2].text = f"{row['p']:.2f}"  # Сила удара, Н (Р)
        data_row.cells[3].text = f"{row['f']:.2f}"  # Сила удара, Н (фильтр)
    
    # Форматирование всех ячеек таблицы (Times New Roman 14 и выравнивание по центру)
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Выравнивание по центру
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(14)


def create_word_document(analysis_data: dict, analysis_uid: Optional[str] = None) -> Document:
    """
    Создает Word документ с более точным форматированием
    
    Args:
        analysis_data: Словарь с данными анализа
        
    Returns:
        Document: Созданный документ
    """
    
    doc = Document()
    
    # Настройка полей страницы
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(1.5)
    
    # Добавляем заголовок с текущей датой
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Первая строка - жирная
    title_paragraph = doc.add_paragraph()
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_paragraph.paragraph_format.line_spacing = 1.0
    title_paragraph.paragraph_format.space_after = Pt(0)
    
    protocol_number = str(analysis_data['analysis']['protocol_number'].iat[0])

    title_run = title_paragraph.add_run(f"ПРОТОКОЛ № {protocol_number} от {current_date} г.")
    title_run.font.name = 'Times New Roman'
    title_run.font.size = Pt(14)
    title_run.bold = True
    
    # Вторая строка - обычная
    subtitle_paragraph = doc.add_paragraph()
    subtitle_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_paragraph.paragraph_format.line_spacing = 1.0
    subtitle_paragraph.paragraph_format.space_after = Pt(0)
    
    subtitle_run = subtitle_paragraph.add_run("Моделирование ударного импульса")
    subtitle_run.font.name = 'Times New Roman'
    subtitle_run.font.size = Pt(14)
    subtitle_run.bold = False

    # Добавляем пустую строку
    empty_paragraph = doc.add_paragraph()
    empty_paragraph.paragraph_format.space_after = Pt(0)
    
    # Создаем абзац для основного текста с правильным форматированием списка
    paragraph = doc.add_paragraph()
    
    # Настройка абзаца для списка
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.left_indent = Cm(0.75)  # Отступ слева
    paragraph.paragraph_format.line_spacing = 1.15
    paragraph.paragraph_format.space_after = Pt(0)
    
    # Добавляем части текста с разным форматированием
    parts = [
        ("1.", True),  # Номер списка ЖИРНЫМ
        (" Объекты исследования", True),  # Заголовок жирным с пробелом
        (": стержневая ударная система: боек – волновод. Среда нагружения – образец из стали 04X19H9 (д*ш*в) 50*100*50 мм. ", False),
        ("Образец размещен на установочном столе прямоугольной формы, размерами (д*ш*в) 220*126*85 мм. ", False),
    ]
    
    for text, is_bold in parts:
        run = paragraph.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.bold = is_bold
    
    # Создаем отдельный абзац для последней строки
    paragraph2 = doc.add_paragraph()
    paragraph2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph2.paragraph_format.left_indent = Cm(0.75)
    paragraph2.paragraph_format.line_spacing = 1.15
    paragraph2.paragraph_format.space_after = Pt(0)
    
    run2 = paragraph2.add_run("Задача решается в симметричной постановке.")
    run2.font.name = 'Times New Roman'
    run2.font.size = Pt(14)
    
    # Добавляем пункт 2 - Параметры элементов ударной системы
    paragraph3 = doc.add_paragraph()
    paragraph3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph3.paragraph_format.left_indent = Cm(0.75)
    paragraph3.paragraph_format.line_spacing = 1.15
    paragraph3.paragraph_format.space_after = Pt(6)
    
    # Номер и заголовок пункта 2
    run3 = paragraph3.add_run("2. Параметры элементов ударной системы:")
    run3.font.name = 'Times New Roman'
    run3.font.size = Pt(14)
    run3.bold = True
    
    # Создаем таблицу с параметрами
    table = doc.add_table(rows=6, cols=3)
    table.style = 'Table Grid'
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Заголовки таблицы
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Параметр'
    header_cells[1].text = 'Расчет'
    header_cells[2].text = 'В симметричной постановке'

    # Настройка заголовков
    for cell in header_cells:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
                run.bold = True
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    m1_kg = float(analysis_data["plan_records"]["m1_kg"].iloc[0])
    l1_m = float(analysis_data["plan_records"]["l1_m"].iloc[0])
    d1_m = float(analysis_data["plan_records"]["d1_m"].iloc[0])
    l2_m = float(analysis_data["plan_records"]["l2_m"].iloc[0])
    d2_m = float(analysis_data["plan_records"]["d2_m"].iloc[0])

    # Данные таблицы
    table_data = [
        ('Длина бойка (L₁), м', f'{l1_m}', '-'),
        ('Диаметр бойка (d₁), м', f'{d1_m}', '-'),
        ('Масса бойка (m₁), кг', f'{m1_kg}', f'{m1_kg/2}'),
        ('Длина волновода (L₂), м', f'{l2_m}', '-'),
        ('Диаметр бойка (d₂), м', f'{d2_m}', '-')
    ]

    for i, (param, calc, sym) in enumerate(table_data, 1):
        row_cells = table.rows[i].cells
        
        # Первый столбец - выравнивание по левому краю
        row_cells[0].text = param
        for paragraph in row_cells[0].paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT  # ЛЕВОЕ выравнивание
        
        # Второй и третий столбцы - выравнивание по центру
        row_cells[1].text = calc
        for paragraph in row_cells[1].paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        row_cells[2].text = sym
        for paragraph in row_cells[2].paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Добавляем описание материала после таблицы
    material_paragraph = doc.add_paragraph()
    material_paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    material_paragraph.paragraph_format.left_indent = Cm(0.75)
    material_paragraph.paragraph_format.line_spacing = 1.15
    material_paragraph.paragraph_format.space_after = Pt(0)
    
    material_run = material_paragraph.add_run("Материал бойка, волновода, стола установочного: конструкционная сталь.")
    material_run.font.name = 'Times New Roman'
    material_run.font.size = Pt(14)

    # Добавляем пункт 3 - Параметры нагружения
    paragraph4 = doc.add_paragraph()
    paragraph4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph4.paragraph_format.left_indent = Cm(0.75)
    paragraph4.paragraph_format.line_spacing = 1.15
    paragraph4.paragraph_format.space_after = Pt(6)
    
    # Номер и заголовок пункта 3
    run4 = paragraph4.add_run("3. Параметры нагружения:")
    run4.font.name = 'Times New Roman'
    run4.font.size = Pt(14)
    run4.bold = True
    
    # Создаем таблицу с параметрами нагружения
    table2 = doc.add_table(rows=6, cols=2)
    table2.style = 'Table Grid'
    table2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Заголовки таблицы
    header_cells2 = table2.rows[0].cells
    header_cells2[0].text = 'Параметр'
    header_cells2[1].text = 'В симметричной постановке'
    
    # Настройка заголовков
    for cell in header_cells2:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
                run.bold = True
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    energy_j = int(float(analysis_data["analysis"]["energy_j"].iloc[0]))
    v = round(float(analysis_data["plan_records"]["v_ms"].iloc[0]), 1)
    p_static_value = int(float(analysis_data["plan_records"]["p_static_value"].iloc[0]))
    p_static = int(float(analysis_data["plan_records"]["p_static"].iloc[0]))
    p_n = int(float(analysis_data["plan_records"]["p_n"].iloc[0]))

    # Данные таблицы нагружения
    loading_data = [
        ('Энергия удара, Дж', f'{energy_j}'),
        ('Скорость удара, м/с', f'{v}'),
        ('Сила удара (P), Н', f'{p_n}'),
        ('Сила статического поджатия бойка к волноводу (Pₛₜ), Н', f'{p_static_value}'),
        ('Доля силы статического поджатия по отношению к силе удара, %', f'{p_static}')
    ]
    
    for i, (param, value) in enumerate(loading_data, 1):
        row_cells = table2.rows[i].cells
        
        # Первый столбец - выравнивание по левому краю
        row_cells[0].text = param
        for paragraph in row_cells[0].paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Второй столбец - выравнивание по центру
        row_cells[1].text = value
        for paragraph in row_cells[1].paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Добавляем пункт 4 - Зависимость силы удара от времени
    paragraph5 = doc.add_paragraph()
    paragraph5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph5.paragraph_format.left_indent = Cm(0.75)
    paragraph5.paragraph_format.line_spacing = 1.15
    paragraph5.paragraph_format.space_after = Pt(0)
    
    # Номер и заголовок пункта 4
    run5 = paragraph5.add_run("4. Зависимость силы удара от времени, полученная в результате моделирования (после фильтра Butterworth 10000Hz):")
    run5.font.name = 'Times New Roman'
    run5.font.size = Pt(14)
    run5.bold = True

    # Получаем пути к изображениям по UUID анализа
    # ВАЖНО: используем переданный analysis_uid (UUID), если он задан,
    # так как имена файлов формируются по нему в utils.run_protocol_analysis
    analysis_id = str(analysis_uid or analysis_data['analysis']['id'].iloc[0])
    analysis_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'analyses')
    
    detailed_image_path = None
    plain_image_path = None
    
    # Ищем изображения по UUID
    if os.path.exists(analysis_dir):
        detailed_filename = f'{analysis_id}_detailed.png'
        plain_filename = f'{analysis_id}_plain.png'
        
        detailed_image_path = os.path.join(analysis_dir, detailed_filename)
        plain_image_path = os.path.join(analysis_dir, plain_filename)
        
        logger.info(f"Поиск изображений для анализа {analysis_id}:")
        logger.info(f"  - detailed: {detailed_image_path} (существует: {os.path.exists(detailed_image_path)})")
        logger.info(f"  - plain: {plain_image_path} (существует: {os.path.exists(plain_image_path)})")
        
        # Проверяем существование файлов
        if not os.path.exists(detailed_image_path):
            detailed_image_path = None
        if not os.path.exists(plain_image_path):
            plain_image_path = None
    else:
        logger.warning(f"Директория с изображениями не найдена: {analysis_dir}")

    if plain_image_path and os.path.exists(plain_image_path):
        try:
            # Доп.проверка: файл не пустой
            try:
                if os.path.getsize(plain_image_path) <= 0:
                    raise ValueError("Файл изображения пустой (0 байт)")
            except Exception:
                pass
            # Создаем абзац для картинки с центрированием
            image_paragraph1 = doc.add_paragraph()
            image_paragraph1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            image_paragraph1.paragraph_format.space_after = Pt(0)
            
            # Добавляем картинку в run абзаца
            run = image_paragraph1.add_run()
            run.add_picture(plain_image_path, width=Cm(12))  # Ширина 12 см
        except Exception as e:
            # Если не удалось добавить картинку, добавляем текст об ошибке
            error_paragraph = doc.add_paragraph()
            error_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            error_run = error_paragraph.add_run(f"Ошибка загрузки изображения: {str(e)}")
            error_run.font.name = 'Times New Roman'
            error_run.font.size = Pt(12)
            error_run.italic = True

    # Добавляем пункт 5 - Зависимость силы удара от времени
    paragraph6 = doc.add_paragraph()
    paragraph6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph6.paragraph_format.left_indent = Cm(0.75)
    paragraph6.paragraph_format.line_spacing = 1.15
    paragraph6.paragraph_format.space_after = Pt(0)
    
    # Номер и заголовок пункта 5
    run6 = paragraph6.add_run("5. Параметры ударного импульса:")
    run6.font.name = 'Times New Roman'
    run6.font.size = Pt(14)
    run6.bold = True

    if detailed_image_path and os.path.exists(detailed_image_path):
        try:
            # Доп.проверка: файл не пустой
            try:
                if os.path.getsize(detailed_image_path) <= 0:
                    raise ValueError("Файл изображения пустой (0 байт)")
            except Exception:
                pass
            # Создаем абзац для картинки с центрированием
            image_paragraph2 = doc.add_paragraph()
            image_paragraph2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            image_paragraph2.paragraph_format.space_after = Pt(0)

            # Добавляем картинку в run абзаца
            run = image_paragraph2.add_run()
            run.add_picture(detailed_image_path, width=Cm(12))  # Ширина 12 см

        except Exception as e:
            # Если не удалось добавить картинку, добавляем текст об ошибке
            error_paragraph = doc.add_paragraph()
            error_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            error_run = error_paragraph.add_run(f"Ошибка загрузки изображения: {str(e)}")
            error_run.font.name = 'Times New Roman'
            error_run.font.size = Pt(12)
            error_run.italic = True

    create_impulse_tables(doc, analysis_data['extrema'])

    # Добавляем пункт 7 - Зависимость силы удара от времени
    paragraph7 = doc.add_paragraph()
    paragraph7.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph7.paragraph_format.left_indent = Cm(0.75)
    paragraph7.paragraph_format.line_spacing = 1.15
    paragraph7.paragraph_format.space_after = Pt(0)
    
    # Номер и заголовок пункта 6
    run7 = paragraph7.add_run(f"6. Данные после моделирования (протокол № {protocol_number}):")
    run7.font.name = 'Times New Roman'
    run7.font.size = Pt(14)
    run7.bold = True

    create_force_records_table(doc, analysis_data['force_records'])

    return doc


def generate_protocol_document(protocol_number: str, analysis_id: str) -> Optional[str]:
    """
    Генерирует Word протокол для указанного номера протокола и сохраняет его в БД
    
    Args:
        protocol_number: Номер протокола
        analysis_id: ID анализа
        
    Returns:
        str: Путь к сохраненному файлу протокола или None в случае ошибки
    """
    try:
        logger.info(f"Начало генерации протокола для протокола {protocol_number}")
        
        # Получаем данные анализа
        analysis_data = get_analysis_by_protocol_number(protocol_number)
        
        if "error" in analysis_data:
            logger.error(f"Ошибка получения данных анализа: {analysis_data['error']}")
            return None
        
        # Создаем Word документ (передаем UUID анализа для корректного поиска изображений)
        doc = create_word_document(analysis_data, analysis_uid=analysis_id)
        
        # Генерируем имя файла по UUID анализа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"protocol_{analysis_id}_{timestamp}.docx"
        
        # Путь для сохранения рядом с картинками
        protocol_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'protocols')
        os.makedirs(protocol_dir, exist_ok=True)
        
        file_path = os.path.join(protocol_dir, filename)
        
        # Сохраняем документ
        doc.save(file_path)
        
        # Сохраняем информацию о протоколе в БД
        from src.modules.impuls_analysis.models import ImpulsAnalysis
        
        analysis = ImpulsAnalysis.objects.get(id=analysis_id)
        
        # Создаем запись протокола
        protocol = ImpulsProtocol.objects.create(
            analysis=analysis,
            protocol_file=f'impuls_analysis/protocols/{filename}',
            file_size=os.path.getsize(file_path)
        )
        
        logger.info(f"Протокол успешно создан: {file_path}, ID в БД: {protocol.id}")
        
        return f'impuls_analysis/protocols/{filename}'
        
    except Exception as e:
        logger.error(f"Ошибка при генерации протокола для протокола {protocol_number}: {str(e)}", exc_info=True)
        return None
