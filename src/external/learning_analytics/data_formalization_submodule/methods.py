import re
import pandas as pd
import os
import traceback
import logging
import json
from typing import Any, Dict, List, Union

# Получение логгера
logger = logging.getLogger(__name__)

def print_result_as_json(result: Dict[str, Any], indent: int = 2, ensure_ascii: bool = False) -> None:
    """
    Выводит результат парсинга в виде правильно форматированного JSON
    с сохранением всех структур данных (списки выводятся в [])

    Args:
        result: Результат работы функции parse_excel_file()
        indent: Количество пробелов для отступа (по умолчанию 2)
        ensure_ascii: Экранировать non-ASCII символы (по умолчанию False)
    """

    def prepare_for_json(data: Any) -> Any:
        """Рекурсивно подготавливает данные для сериализации в JSON"""
        if data is None:
            return None
        elif isinstance(data, (str, int, float, bool)):
            return data
        elif isinstance(data, dict):
            return {k: prepare_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [prepare_for_json(item) for item in data]
        else:
            return str(data)

    # Подготавливаем данные и выводим JSON
    formatted = prepare_for_json(result)
    print(json.dumps(formatted, indent=indent, ensure_ascii=ensure_ascii))


def get_excel_structure_as_json(file_path: str, sheet_name: str = None, limit_rows: int = 5) -> Dict[str, Any]:
    """
    Читает Excel файл и возвращает его структуру в виде JSON
    
    Args:
        file_path: Путь к Excel файлу
        sheet_name: Имя конкретного листа для чтения (если None, то читаются все листы)
        limit_rows: Ограничение на количество строк для чтения (для предварительного просмотра)
        
    Returns:
        Dict с структурой данных из Excel файла
    """
    result = {}
    
    try:
        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            logger.error(f"Файл не существует по пути: {file_path}")
            return {
                "success": False,
                "error": f"Файл не найден по пути: {file_path}"
            }
            
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        logger.info(f"Размер файла: {file_size} байт")
        if file_size == 0:
            logger.error("Файл пуст")
            return {
                "success": False,
                "error": "Файл имеет нулевой размер"
            }
            
        logger.info(f"Начинаем чтение Excel файла: {file_path}")
        
        if sheet_name:
            # Если указано конкретное имя листа
            logger.info(f"Чтение конкретного листа: {sheet_name}")
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=limit_rows)
                logger.info(f"Лист {sheet_name} прочитан, размер: {df.shape}")
                
                headers = list(df.columns)
                preview_data = df.values.tolist()
                
                result = {
                    "success": True,
                    "sheet_name": sheet_name,
                    "headers": headers,
                    "preview_data": preview_data,
                    "full_data": df.to_dict('records')
                }
            except Exception as e:
                logger.error(f"Ошибка при чтении листа {sheet_name}: {str(e)}")
                return {
                    "success": False,
                    "error": f"Ошибка при чтении листа '{sheet_name}': {str(e)}"
                }
        else:
            # Читаем все листы
            logger.info("Чтение всех листов (лист не указан)")
            try:
                xls = pd.ExcelFile(file_path)
                logger.info(f"Найдены листы: {xls.sheet_names}")
                sheets = {}
                
                for sheet in xls.sheet_names:
                    logger.info(f"Обработка листа: {sheet}")
                    df = pd.read_excel(xls, sheet_name=sheet, nrows=limit_rows)
                    logger.info(f"Лист {sheet} прочитан, размер: {df.shape}")
                    
                    headers = list(df.columns)
                    preview_data = df.values.tolist()
                    
                    sheets[sheet] = {
                        "headers": headers,
                        "preview_data": preview_data,
                        "full_data": df.to_dict('records')
                    }
                
                result = {
                    "success": True,
                    "sheets": sheets
                }
            except Exception as e:
                logger.error(f"Ошибка при работе с листами Excel файла: {str(e)}")
                return {
                    "success": False,
                    "error": f"Ошибка при открытии Excel файла: {str(e)}"
                }
                
    except Exception as e:
        logger.error(f"Ошибка при обработке Excel файла: {str(e)}")
        result = {
            "success": False,
            "error": str(e)
        }
    
    logger.info(f"Завершена обработка Excel файла, успех: {result.get('success', False)}")
    return result

def parse_excel_file(file_path):
    """Основная функция для парсинга Excel файла с учебным планом"""
    xls = pd.ExcelFile(file_path)
    result = {}

    # Обработка листа "Титул"
    if "Титул" in xls.sheet_names:
        df_titul = pd.read_excel(xls, sheet_name="Титул")
        titul_data = parse_titul_sheet(df_titul)
        result['titul'] = titul_data

    # Обработка листа "ПланСвод"
    if "ПланСвод" in xls.sheet_names:
        df_plan = pd.read_excel(xls, sheet_name="ПланСвод")
        plan_data = parse_plan_sheet(df_plan)
        result['plan'] = plan_data
        valid_codes = extract_valid_codes(plan_data)
    else:
        valid_codes = set()

    # Обработка листа "Компетенции(2)"
    if "Компетенции(2)" in xls.sheet_names:
        df_comp = pd.read_excel(xls, sheet_name="Компетенции(2)")
        competencies = parse_competencies_sheet(df_comp, valid_codes)
        result['competencies'] = competencies
    else:
        result['competencies'] = []

    return result


def extract_valid_codes(plan_data):
    """Извлекает валидные коды дисциплин из данных плана"""
    valid_codes = set()

    if "discipline" in plan_data:
        for discipline in plan_data["discipline"]:
            if code := discipline.get("code"):
                valid_codes.add(code)

    return valid_codes


def parse_competencies_sheet(df, valid_codes):
    """Парсинг листа с компетенциями"""
    competencies_data = []

    for _, row in df.iterrows():
        code_cell = row.iloc[2] if len(row) > 2 else None
        comp_cell = row.iloc[5] if len(row) > 5 else None

        if pd.isna(code_cell) or pd.isna(comp_cell):
            continue

        code = normalize_code(str(code_cell).strip())
        comp_str = str(comp_cell).strip()

        if not code or not comp_str:
            continue

        competencies = [c.strip() for c in comp_str.split(";") if c.strip()]
        competencies_data.append({
            "code": code,
            "competency": competencies
        })

    return competencies_data


def normalize_code(raw_code):
    """Нормализует код дисциплины"""
    code = re.split(r'[()]', raw_code)[0].strip()
    return code.upper()


def parse_titul_sheet(df):
    """Парсинг титульного листа"""
    all_data = df_to_list(df)

    return {
        "speciality": parse_specialty_info(all_data),
        "curriculum": parse_curriculum_info(all_data)
    }


def df_to_list(df):
    """Конвертирует DataFrame в список строк"""
    return [
        [str(cell) if pd.notna(cell) else "" for cell in row]
        for _, row in df.iterrows()
    ]


def parse_specialty_info(data):
    """Парсинг информации о специальности"""
    result = {
        "code": None,
        "name": None,
        "specialization": None,
        "department": None,
        "faculty": None
    }

    result.update(find_code_and_name(data))
    result["specialization"] = find_specialization(data)
    result.update(find_department_and_faculty(data))

    return result


def find_code_and_name(data):
    """Поиск кода и названия специальности"""
    for row in data:
        for cell in row:
            if not isinstance(cell, str):
                continue

            if match := re.search(r'(\d{2}\.\d{2}\.\d{2})\s*(.+)', cell.strip()):
                return {"code": match.group(1), "name": match.group(2)}

    return {}


def find_specialization(data):
    """Поиск специализации/профиля/программы магистратуры"""
    candidates = []

    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            if not isinstance(cell, str):
                continue

            cell_lower = cell.lower()
            if not any(kw in cell_lower for kw in ["специализация", "профиль", "программа магистратуры"]):
                continue

            value = find_adjacent_value(data, i, j)
            if not value:
                continue

            clean_value = clean_specialization_value(value)
            if clean_value:
                candidates.append(clean_value)

    return select_best_candidate(candidates) if candidates else None


def find_adjacent_value(data, row_idx, col_idx):
    """Ищет значение в соседних ячейках"""
    # Проверяем справа
    if col_idx + 1 < len(data[row_idx]) and data[row_idx][col_idx + 1].strip():
        return data[row_idx][col_idx + 1].strip()
    # Проверяем снизу
    elif row_idx + 1 < len(data) and col_idx < len(data[row_idx + 1]) and data[row_idx + 1][col_idx].strip():
        return data[row_idx + 1][col_idx].strip()
    return None


def clean_specialization_value(value):
    """Очищает значение специализации"""
    if match := re.search(r'"([^"]+)"', value):
        return match.group(1)

    return re.sub(
        r'(специализация|профиль|программа\s*магистратуры)\s*[nN]?\d?\s*[:"-]*\s*',
        '',
        value,
        flags=re.IGNORECASE
    ).strip()


def select_best_candidate(candidates):
    """Выбирает лучшего кандидата на специализацию"""
    for candidate in candidates:
        if "магистратур" in candidate.lower():
            return candidate
    return candidates[0]


def find_department_and_faculty(data):
    """Поиск кафедры и факультета"""
    result = {"department": None, "faculty": None}

    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            if not isinstance(cell, str):
                continue

            cell_lower = cell.lower()
            if "кафедра" in cell_lower and not result["department"]:
                result["department"] = find_adjacent_value(data, i, j)
            elif "факультет" in cell_lower and not result["faculty"]:
                result["faculty"] = find_adjacent_value(data, i, j)

    return result


def parse_curriculum_info(data):
    """Парсинг информации об учебном плане"""
    return {
        "education_duration": find_education_duration(data),
        "year_of_admission": find_year_of_admission(data),
        "is_active": True
    }


def find_year_of_admission(data):
    """Поиск года начала подготовки с улучшенной логикой"""
    # Сначала ищем по точному совпадению
    for row_idx, row in enumerate(data):
        for col_idx, cell in enumerate(row):
            if not isinstance(cell, str):
                continue

            cell_lower = cell.lower()

            # Ищем стандартную фразу о годе начала
            if "год начала подготовки" in cell_lower:
                # Ищем год в текущей строке справа
                for k in range(col_idx + 1, len(row)):
                    if year := extract_year_from_cell(row[k]):
                        return year

                # Ищем год в следующей строке
                if len(data) > row_idx + 1:
                    next_row = data[row_idx + 1]
                    for cell in next_row:
                        if year := extract_year_from_cell(cell):
                            return year

            # Альтернативный вариант поиска по слову "утверждаю"
            elif "утверждаю" in cell_lower:
                if year := extract_year_from_cell(cell):
                    return year

                # Проверяем соседние ячейки
                for k in range(max(0, col_idx - 2), min(len(row), col_idx + 3)):
                    if year := extract_year_from_cell(row[k]):
                        return year

    # Если не нашли по ключевым словам, ищем любой 4-значный год в данных
    for row in data:
        for cell in row:
            if isinstance(cell, str) and (year := extract_year_from_cell(cell)):
                return year

    return None


def extract_year_from_cell(cell):
    """Извлекает год из ячейки (20XX)"""
    if not isinstance(cell, str):
        return None

    # Ищем 4 цифры подряд, начинающиеся с 20
    if match := re.search(r'(20\d{2})', cell):
        year = match.group(1)
        # Проверяем что год в разумных пределах
        if 2000 <= int(year) <= 2100:
            return year
    return None


def search_year_in_row(row, start_col):
    """Ищет год в строке начиная с указанного столбца"""
    for k in range(start_col + 1, len(row)):
        if match := re.search(r'(20\d{2})', str(row[k])):
            return match.group(1)
    return None


def find_education_duration(data):
    """Поиск срока обучения"""
    for row in data:
        for cell in row:
            cell_str = str(cell)
            if "срок получения образования" not in cell_str.lower():
                continue

            years_match = re.search(r'(\d+)\s*[лг]', cell_str.lower())
            months_match = re.search(r'(\d+)\s*м', cell_str.lower())

            years = int(years_match.group(1)) if years_match else 0
            months = int(months_match.group(1)) if months_match else 0

            total_months = years * 12 + months
            return (total_months + 5) // 6  # Округление вверх до семестров

    return None


def parse_plan_sheet(df):
    """Парсинг сводного плана"""
    return {
        "base_discipline": parse_base_disciplines(df),
        "discipline": parse_detailed_disciplines(df)
    }


def parse_detailed_disciplines(df):
    """Парсинг детальной информации о дисциплинах"""
    disciplines = []

    for _, row in df.iterrows():
        if not is_valid_discipline_row(row):
            continue

        code = str(row.iloc[1]).strip()
        name = str(row.iloc[2]).strip()

        if should_skip_discipline(name):
            continue

        disciplines.append({
            "curriculum": None,
            "base_discipline": None,
            "code": code,
            "name": name,
            "semesters": extract_semesters_from_row(row),
            "contact_work_hours": parse_hours(row, 13),
            "independent_work_hours": parse_hours(row, 14),
            "control_work_hours": parse_hours(row, 15),
            "technologies": None,
            "competencies": None
        })

    return disciplines


def is_valid_discipline_row(row):
    """Проверяет, является ли строка валидной дисциплиной"""
    if len(row) == 0 or pd.isna(row.iloc[0]):
        return False
    return str(row.iloc[0]).strip() == "+"


def should_skip_discipline(name):
    """Определяет, нужно ли пропускать дисциплину"""
    skip_keywords = [
        "элективные", "спортивная подготовка", "физическая культура",
        "спорт", "дисциплина по выбору", "практика", "защита",
        "подготовка к защите", "выпускная квалификационная работа"
    ]
    name_lower = name.lower()
    return any(kw in name_lower for kw in skip_keywords)


def extract_semesters_from_row(row):
    """Извлекает семестры из строки дисциплины"""
    semesters = set()

    for col_idx in [3, 4, 5]:  # Колонки с экзаменами и зачетами
        if len(row) > col_idx and pd.notna(row.iloc[col_idx]):
            semesters.update(parse_semester_value(row.iloc[col_idx]))

    return format_semesters(semesters)


def parse_semester_value(value):
    """Парсит значение семестра из ячейки"""
    value_str = str(value).strip()
    parts = re.split(r'[,;|]', value_str)
    semesters = set()

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if len(part) == 1 and (part.isdigit() or part.isalpha()):
            semesters.add(part)
        elif part.isdigit() and len(part) > 1:
            semesters.update(list(part))

    return semesters


def format_semesters(semesters):
    """Форматирует семестры в строку"""
    return ", ".join(sorted(semesters, key=lambda x: (not x.isdigit(), x)))


def parse_hours(row, col_idx):
    """Парсит количество часов из указанной колонки"""
    if len(row) <= col_idx or pd.isna(row.iloc[col_idx]):
        return None
    try:
        return int(float(row.iloc[col_idx]))
    except (ValueError, TypeError):
        return None


def parse_base_disciplines(df):
    """Парсинг базовых дисциплин"""
    return [
        {
            "code": str(row.iloc[1]).strip(),
            "name": str(row.iloc[2]).strip(),
            "description": None
        }
        for _, row in df.iterrows()
        if is_valid_discipline_row(row) and not should_skip_discipline(str(row.iloc[2]).strip())
    ]

def get_excel_summary(file_path: str) -> Dict[str, Any]:
    """
    Извлекает краткую информацию о файле учебного плана
    
    Args:
        file_path: Путь к Excel файлу
        
    Returns:
        Dict с ключевой информацией о файле (специальность, год поступления и т.д.)
    """
    try:
        logger.info(f"===== ИЗВЛЕЧЕНИЕ ИНФОРМАЦИИ О ФАЙЛЕ =====")
        logger.info(f"Извлечение краткой информации из файла: {file_path}")
        
        # Используем существующую функцию parse_excel_file
        parsed_data = parse_excel_file(file_path)
        logger.info(f"Данные были извлечены из файла, структура: {parsed_data.keys()}")
        
        # Извлекаем ключевую информацию
        summary = {
            "success": True,
            "summary": {}
        }
        
        # Информация о специальности
        if titul_data := parsed_data.get('titul', {}):
            logger.info(f"Данные титульного листа: {titul_data.keys()}")
            specialty_info = titul_data.get('speciality', {})
            curriculum_info = titul_data.get('curriculum', {})
            
            logger.info(f"Данные о специальности: {specialty_info}")
            logger.info(f"Данные об учебном плане: {curriculum_info}")
            
            # Формируем краткую информацию
            summary_data = {}
            
            if specialty_code := specialty_info.get('code'):
                summary_data['specialty_code'] = specialty_code
            
            if specialty_name := specialty_info.get('name'):
                summary_data['specialty_name'] = specialty_name
            
            if specialization := specialty_info.get('specialization'):
                summary_data['specialization'] = specialization
            
            if department := specialty_info.get('department'):
                summary_data['department'] = department
            
            if faculty := specialty_info.get('faculty'):
                summary_data['faculty'] = faculty
            
            if year_of_admission := curriculum_info.get('year_of_admission'):
                summary_data['year_of_admission'] = year_of_admission
            
            if education_duration := curriculum_info.get('education_duration'):
                summary_data['education_duration'] = education_duration
            
            summary['summary'] = summary_data
        
        # Информация о компетенциях
        if competencies := parsed_data.get('competencies', []):
            summary['competencies_count'] = len(competencies)
        
        # Информация о дисциплинах
        if plan_data := parsed_data.get('plan', {}):
            if disciplines := plan_data.get('discipline', []):
                summary['disciplines_count'] = len(disciplines)
        
        return summary
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении краткой информации из файла: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": f"Не удалось извлечь информацию: {str(e)}"
        }