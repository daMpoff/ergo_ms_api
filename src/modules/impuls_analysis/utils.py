"""
Утилиты для модуля анализа импульса.
Обработка Excel файлов и генерация протоколов.
"""

import logging
import re
import io

from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

from src.modules.impuls_analysis.models import (
    ImpulsAnalysis,
    ImpulsForceRecord,
    ImpulsPlanRecord,
)

logger = logging.getLogger('impuls_analysis')


class ImpulsExcelProcessor:
    """
    Класс для обработки Excel файлов анализа импульса
    """
    
    def __init__(self):
        self.logger = logging.getLogger('celery.module.impuls_analysis.excel_processing')
    
    def process_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Обрабатывает Excel файл
        
        Args:
            file_path: Путь к файлу
            file_type: Тип файла (force_calculation или experiment_plan)
            
        Returns:
            Словарь с обработанными данными
        """
        self.logger.info(f"Обработка файла {file_path} типа {file_type}")

        if file_type == 'force_calculation':
            return self._process_force_calculation(file_path)
        elif file_type == 'experiment_plan':
            return self._process_experiment_plan(file_path)
        else:
            raise ValueError(f"Неизвестный тип файла: {file_type}")
    
    def _process_force_calculation(self, file_path: str) -> Dict[str, Any]:
        """
        Обрабатывает файл расчета силы
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с данными расчета силы
        """
        wb = load_workbook(filename=file_path, data_only=True, read_only=True)

        sheets_data: List[Dict[str, Any]] = []

        for ws in wb.worksheets:
            # Общие значения для листа
            energy_j = self._get_numeric(ws, 'C5')  # Энергия удара, Дж
            velocity_ms = self._get_numeric(ws, 'D5')  # Скорость удара, м/с
            force_n = self._get_numeric(ws, 'E5')  # Сила удара (P), Н

            # Сканируем протоколы: номера в G2, K2, O2, ... (через каждые 3 столбца)
            # Соответствующие проценты: G4, K4, O4, ...
            # Блок данных для каждого протокола: 3 столбца, начиная с F, пропуск 1 столбца, затем J, ...
            protocol_header_cols = self._iter_cols(start_col='G', step=4) # G,K,O,...
            data_block_start_cols  = self._iter_cols(start_col='F', step=4) # F,J,N,...

            protocols: List[Dict[str, Any]] = []
            # Жесткие границы листа для предотвращения бесконечных обходов
            max_row = ws.max_row or 0
            max_col = ws.max_column or 0

            for (hdr_col_letter, data_col_letter) in zip(protocol_header_cols, data_block_start_cols):
                # Прерываем, если заголовочный столбец вышел за пределы фактически используемых столбцов
                hdr_col_idx = self._col_letter_to_index(hdr_col_letter)
                if hdr_col_idx > max_col:
                    break

                header_cell_addr = f"{hdr_col_letter}2"
                header_val = self._get_cell_value(ws, header_cell_addr)

                if header_val is None or str(header_val).strip() == '':
                    # Как только встретили пустой номер протокола — считаем, что дальше протоколов нет
                    break

                protocol_number = self._clean_protocol_number(str(header_val))

                # Процент статического поджатия из строки 4 (например: "Pст (1%)")
                pct_addr = f"{hdr_col_letter}4"
                pct_val_raw = self._get_cell_value(ws, pct_addr)
                static_press_pct = self._extract_percent_from_text(str(pct_val_raw) if pct_val_raw is not None else '')

                # Данные протокола: три столбца блока: data_col_letter, next, next
                time_col = data_col_letter
                force_col = self._next_col_letter(time_col)
                freq_col = self._next_col_letter(force_col)

                # Если любой из столбцов блока выходит за пределы заполненных столбцов — прекращаем обработку
                time_idx = self._col_letter_to_index(time_col)
                force_idx = self._col_letter_to_index(force_col)
                freq_idx = self._col_letter_to_index(freq_col)
                if max(time_idx, force_idx, freq_idx) > max_col:
                    break

                # Заголовки ожидаются на строке 5 для двух последних столбцов, время с 6-й строки
                # Данные идут построчно до первой полностью пустой тройки ячеек
                rows: List[Dict[str, Optional[float]]] = []
                row_idx = 6
                empty_rows = 0
                max_empty_rows = 50  # страховка на случай редких пустых вставок

                while row_idx <= max_row:
                    t_val = self._get_numeric(ws, f"{time_col}{row_idx}")
                    f_val = self._get_numeric(ws, f"{force_col}{row_idx}")
                    fr_val = self._get_numeric(ws, f"{freq_col}{row_idx}")

                    if t_val is None and f_val is None and fr_val is None:
                        empty_rows += 1
                        if empty_rows >= 3:  # три подряд пустых строки — конец блока
                            break
                    else:
                        empty_rows = 0
                        rows.append({
                            'time_s': t_val,
                            'force_n': f_val,
                            'freq_hz': fr_val,
                        })

                    # Жесткое ограничение на число строк, чтобы избежать бесконечных циклов
                    if row_idx - 6 > 200000:
                        break

                    row_idx += 1

                protocols.append({
                    'protocol_number': protocol_number,
                    'static_preload_pct': static_press_pct,
                    'columns': {
                        'time_col': time_col,
                        'force_col': force_col,
                        'freq_col': freq_col,
                    },
                    'rows_count': len(rows),
                    'data': rows,
                })

            sheets_data.append({
                'globals': {
                    'impact_energy_j': energy_j,
                    'impact_velocity_ms': velocity_ms,
                    'impact_force_n': force_n,
                },
                'protocols': protocols,
            })

        result: Dict[str, Any] = {
            'file_type': 'force_calculation',
            'processed_at': datetime.utcnow().isoformat() + 'Z',
            'sheets_count': len(wb.worksheets),
            'sheets': sheets_data,
            'status': 'processed',
        }

        try:
            wb.close()
        except Exception:
            pass

        return result
    
    def _process_experiment_plan(self, file_path: str) -> Dict[str, Any]:
        """
        Обрабатывает файл плана эксперимента
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с данными плана эксперимента
        """
        # Так как формат не регламентирован, извлекаем числовые таблицы по всем листам.
        # Для каждого листа собираем прямоугольный диапазон данных, приводим значения к числам, прочее — None.
        wb = load_workbook(filename=file_path, data_only=True, read_only=True)

        sheets: List[Dict[str, Any]] = []
        total_rows = 0
        total_cols_max = 0

        for ws in wb.worksheets:
            sheet_title: str = ws.title or ''

            # Определяем используемые границы листа
            max_row = ws.max_row or 0
            max_col = ws.max_column or 0
            total_rows += max_row
            total_cols_max = max(total_cols_max, max_col)

            data_matrix: List[List[Optional[float]]] = []

            for r in range(1, max_row + 1):
                row_vals: List[Optional[float]] = []
                for c in range(1, max_col + 1):
                    cell = ws.cell(row=r, column=c)
                    # Берём только числа; строки парсим в числа, прочее — None
                    row_vals.append(self._to_float(cell.value))
                # Обрезаем хвостовые None, чтобы снизить объём
                while row_vals and row_vals[-1] is None:
                    row_vals.pop()
                data_matrix.append(row_vals)

            # Удаляем хвостовые полностью пустые строки
            while data_matrix and all(v is None for v in data_matrix[-1]):
                data_matrix.pop()

            sheets.append({
                'sheet_title': sheet_title,
                'rows': data_matrix,
                'rows_count': len(data_matrix),
                'columns_count_max': max((len(r) for r in data_matrix), default=0),
            })

        result: Dict[str, Any] = {
            'file_type': 'experiment_plan',
            'processed_at': datetime.utcnow().isoformat() + 'Z',
            'sheets_count': len(sheets),
            'summary': {
                'total_rows': total_rows,
                'max_columns': total_cols_max,
            },
            'sheets': sheets,
            'status': 'processed',
        }

        try:
            wb.close()
        except Exception:
            pass

        return result

    # ============ Вспомогательные методы ============

    def _get_cell_value(self, ws, addr: str):
        cell: Cell = ws[addr]
        return cell.value

    def _col_letter_to_index(self, col_letter: str) -> int:
        col_letter = col_letter.upper()
        result = 0
        for ch in col_letter:
            if 'A' <= ch <= 'Z':
                result = result * 26 + (ord(ch) - ord('A') + 1)
        return result

    def _index_to_col_letter(self, index: int) -> str:
        letters = ''
        while index > 0:
            index, rem = divmod(index - 1, 26)
            letters = chr(rem + ord('A')) + letters
        return letters

    def _next_col_letter(self, col_letter: str) -> str:
        return self._index_to_col_letter(self._col_letter_to_index(col_letter) + 1)

    def _iter_cols(self, start_col: str, step: int):
        index = self._col_letter_to_index(start_col)
        # Генератор потенциально бесконечный — управляйте снаружи
        while True:
            yield self._index_to_col_letter(index)
            index += step

    def _to_float(self, value) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().replace(' ', '')
        if s == '':
            return None
        # Заменим запятую на точку, удалим недесятичные символы кроме . - и e
        s = s.replace(',', '.')
        m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", s)
        if not m:
            return None
        try:
            return float(m.group(0))
        except ValueError:
            return None

    def _get_numeric(self, ws, addr: str) -> Optional[float]:
        return self._to_float(self._get_cell_value(ws, addr))

    def _clean_protocol_number(self, raw: str) -> str:
        # Удаляем лидирующее "№" и лишние пробелы
        raw = raw.strip()
        raw = re.sub(r"^[№#\s]*", '', raw, flags=re.IGNORECASE)
        return raw.strip()

    def _extract_percent_from_text(self, text: str) -> Optional[float]:
        # Ожидается вид "Pст (1%)" — извлекаем число в скобках
        # Поддержка вариантов с запятой: 1,5%
        m = re.search(r"\(([-+]?\d+(?:[\.,]\d+)?)%\)", text)
        if not m:
            # fallback: искать первое число, затем знак %
            m = re.search(r"([-+]?\d+(?:[\.,]\d+)?)\s*%", text)
        if not m:
            return None
        try:
            return float(m.group(1).replace(',', '.'))
        except ValueError:
            return None
    
    def validate_file(self, file_path: str, file_type: str) -> bool:
        """
        Валидирует Excel файл
        
        Args:
            file_path: Путь к файлу
            file_type: Тип файла
            
        Returns:
            True если файл валиден
        """
        # TODO: Реализовать валидацию Excel файла
        return True

    # ====== Публичные функции парсинга для сохранения в БД ======

    def parse_force_records(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Парсит файл расчета силы в плоские записи по образцу ноутбука:
        [protocol_number, pct_static, v, p, f, energy_j, velocity_ms, force_n]
        """
        wb = load_workbook(filename=file_path, data_only=True, read_only=True)
        records: List[Dict[str, Any]] = []
        try:
            for ws in wb.worksheets:
                energy_j = self._get_numeric(ws, 'C5')
                velocity_ms = self._get_numeric(ws, 'D5')
                force_n = self._get_numeric(ws, 'E5')

                # собрать номера протоколов и проценты
                protocol_numbers = self._values_by_step(ws, 'G2', step_cols=4, stop_when_empty=True)
                protocol_numbers = [self._clean_protocol_number(str(n)) for n in protocol_numbers]
                pct_static_values = self._values_by_step(ws, 'G4', step_cols=4, stop_when_empty=True)
                pct_static_values = [self._extract_percent_from_text(str(v)) for v in pct_static_values]

                # собрать матрицу F..H, J..L, ... со срезами по фактически заполненным ячейкам
                matrix = self._read_step_blocks(ws, start_col_letter='F', start_row=6, block_width=3, gap=1)

                if not matrix:
                    continue

                n_rows = len(matrix)
                n_cols = len(matrix[0])
                n_blocks_in_matrix = n_cols // 3
                n_blocks = min(len(protocol_numbers), len(pct_static_values), n_blocks_in_matrix)

                for b in range(n_blocks):
                    pnum = protocol_numbers[b]
                    pct = pct_static_values[b]
                    c0, c1, c2 = b * 3, b * 3 + 1, b * 3 + 2
                    for r in range(n_rows):
                        v_val = matrix[r][c0]
                        p_val = matrix[r][c1]
                        f_val = matrix[r][c2]
                        # можно пропускать полностью пустые тройки
                        if v_val in (None, '') and p_val in (None, '') and f_val in (None, ''):
                            continue
                        records.append({
                            'sheet_title': getattr(ws, 'title', '') or '',
                            'protocol_number': pnum,
                            'pct_static': pct,
                            'v': self._to_float(v_val),
                            'p': self._to_float(p_val),
                            'f': self._to_float(f_val),
                            'energy_j': energy_j,
                            'velocity_ms': velocity_ms,
                            'force_n': force_n,
                        })
        finally:
            try:
                wb.close()
            except Exception:
                pass
        return records

    def parse_plan_records(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Парсит файл плана эксперимента в записи по образцу ноутбука.
        Берём блоки строк (каждые 3 строки), протоколы из N:X, значения p_static_value из той же строки.
        """
        wb = load_workbook(filename=file_path, data_only=True, read_only=True)
        records: List[Dict[str, Any]] = []
        try:
            ws = wb.active

            def parse_pct(text):
                if text is None:
                    return None
                m = re.search(r"\(([\d.,]+)\s*%?\)", str(text))
                return float(m.group(1).replace(',', '.')) if m else None

            data_start_row = 8
            header_start_row = 7
            step = 3

            from openpyxl.utils.cell import column_index_from_string, get_column_letter

            data_min_c = column_index_from_string('C')
            data_max_c = column_index_from_string('V')
            prot_min_c = column_index_from_string('N')
            prot_max_c = column_index_from_string('X')

            # Заголовки данных C..M из 5 строки
            data_headers = [ws.cell(row=5, column=c).value or get_column_letter(c)
                            for c in range(column_index_from_string('C'), column_index_from_string('M') + 1)]

            # Pст проценты из N5:X5
            pstat_labels_row = 5
            pstat_labels = next(ws.iter_rows(min_row=pstat_labels_row, max_row=pstat_labels_row,
                                             min_col=prot_min_c, max_col=prot_max_c, values_only=True))
            pstat_pct_by_col = {prot_min_c + i: parse_pct(v) for i, v in enumerate(pstat_labels)}

            r_data, r_head = data_start_row, header_start_row
            while r_data <= ws.max_row:
                prot_row = next(ws.iter_rows(min_row=r_head, max_row=r_head,
                                             min_col=prot_min_c, max_col=prot_max_c,
                                             values_only=True))
                data_row = next(ws.iter_rows(min_row=r_data, max_row=r_data,
                                             min_col=data_min_c, max_col=data_max_c,
                                             values_only=True))
                pstatic_values_row = next(ws.iter_rows(min_row=r_data, max_row=r_data,
                                                       min_col=prot_min_c, max_col=prot_max_c,
                                                       values_only=True))

                if all(p in (None, '') for p in prot_row) and all(v in (None, '') for v in data_row):
                    break
                if all(v in (None, '') for v in data_row):
                    break

                for i, p in enumerate(prot_row):
                    if p in (None, ''):
                        continue
                    col_idx = prot_min_c + i
                    rec: Dict[str, Any] = {
                        'protocol_number': self._clean_protocol_number(str(p)),
                        'p_static': pstat_pct_by_col.get(col_idx),
                        'p_static_value': self._to_float(pstatic_values_row[i]),
                    }
                    # сопоставляем только C..M
                    values = list(data_row)[:len(data_headers)]
                    for name, val in zip(data_headers, values):
                        rec[name] = self._to_float(val)
                    records.append(rec)

                r_data += step
                r_head += step
        finally:
            try:
                wb.close()
            except Exception:
                pass
        return records

    # ====== Низкоуровневые помощники из ноутбука ======

    def _values_by_step(self, ws, start_addr: str, step_cols: int = 4, stop_when_empty: bool = True, max_col: Optional[int] = None) -> List[Any]:
        from openpyxl.utils.cell import coordinate_from_string, column_index_from_string, get_column_letter
        col_letter, row = coordinate_from_string(start_addr)
        col = column_index_from_string(col_letter)
        vals = []
        while True:
            addr = f"{get_column_letter(col)}{row}"
            v = ws[addr].value
            if stop_when_empty and (v is None or v == ""):
                break
            vals.append(v)
            col += step_cols
            if max_col and col > max_col:
                break
        return vals

    def _read_step_blocks(self, ws, start_col_letter: str = 'F', start_row: int = 6, block_width: int = 3, gap: int = 1) -> List[List[Any]]:
        from openpyxl.utils.cell import column_index_from_string
        start_col = column_index_from_string(start_col_letter)
        step = block_width + gap
        col_indices: List[int] = []
        c = start_col
        while c <= ws.max_column:
            for i in range(block_width):
                if c + i <= ws.max_column:
                    col_indices.append(c + i)
            c += step
        if not col_indices:
            return []
        min_c, max_c = col_indices[0], col_indices[-1]
        offset = min_c
        data: List[List[Any]] = []
        last_nonempty_row = -1
        rightmost_used_idx = -1
        for r, row_vals in enumerate(
            ws.iter_rows(min_row=start_row, max_row=ws.max_row, min_col=min_c, max_col=max_c, values_only=True),
            start=start_row,
        ):
            picked = [row_vals[c - offset] for c in col_indices]
            any_nonempty = False
            for j, v in enumerate(picked):
                if v not in (None, ''):
                    any_nonempty = True
                    if j > rightmost_used_idx:
                        rightmost_used_idx = j
            data.append(picked)
            if any_nonempty:
                last_nonempty_row = r
        if last_nonempty_row == -1 or rightmost_used_idx == -1:
            return []
        rows_to = last_nonempty_row - start_row + 1
        cols_to = rightmost_used_idx + 1
        data = [row[:cols_to] for row in data[:rows_to]]
        return data


class ImpulsProtocolGenerator:
    """
    Класс для генерации протоколов анализа импульса
    """
    
    def __init__(self):
        self.logger = logging.getLogger('celery.module.impuls_analysis.protocol_generation')
    
    def generate_protocol(self, analysis: ImpulsAnalysis) -> bytes:
        """
        Генерирует протокол анализа в формате Word
        
        Args:
            analysis: Объект анализа импульса
            
        Returns:
            Содержимое файла протокола в байтах
        """
        self.logger.info(f"Генерация протокола для анализа {analysis.id}")
        
        # TODO: Реализовать генерацию Word документа
        # Пока возвращаем заглушку
        
        protocol_content = self._create_protocol_content(analysis)
        return protocol_content.encode('utf-8')
    
    def _create_protocol_content(self, analysis: ImpulsAnalysis) -> str:
        """
        Создает содержимое протокола
        
        Args:
            analysis: Объект анализа импульса
            
        Returns:
            Текст протокола
        """
        # TODO: Реализовать создание содержимого протокола
        # Пока возвращаем заглушку
        
        protocol_text = f"""
ПРОТОКОЛ АНАЛИЗА ИМПУЛЬСА

Название анализа: {analysis.title}
Номер протокола: {analysis.protocol_number or 'Не указан'}
Дата создания: {analysis.created_at.strftime('%d.%m.%Y %H:%M')}
Статус: {analysis.get_status_display()}

Описание:
{analysis.description or 'Описание отсутствует'}

Результаты анализа:
{self._format_results(getattr(analysis, 'analysis_results', None))}

---
Сгенерировано автоматически
        """
        
        return protocol_text.strip()
    
    def _format_results(self, results: Dict[str, Any]) -> str:
        """
        Форматирует результаты анализа для протокола
        
        Args:
            results: Результаты анализа
            
        Returns:
            Отформатированный текст результатов
        """
        if not results:
            return "Результаты анализа отсутствуют"
        
        formatted = []
        for key, value in results.items():
            if isinstance(value, dict):
                formatted.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    formatted.append(f"  {sub_key}: {sub_value}")
            else:
                formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    def generate_bulk_protocol(self, analyses: list) -> bytes:
        """
        Генерирует сводный протокол для нескольких анализов
        
        Args:
            analyses: Список анализов
            
        Returns:
            Содержимое сводного протокола в байтах
        """
        self.logger.info(f"Генерация сводного протокола для {len(analyses)} анализов")
        
        # TODO: Реализовать генерацию сводного протокола
        # Пока возвращаем заглушку
        
        summary_content = f"""
СВОДНЫЙ ПРОТОКОЛ АНАЛИЗОВ ИМПУЛЬСА

Количество анализов: {len(analyses)}
Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Список анализов:
"""
        
        for i, analysis in enumerate(analyses, 1):
            summary_content += f"""
{i}. {analysis.title}
   Протокол: {analysis.protocol_number or 'Не указан'}
   Статус: {analysis.get_status_display()}
   Дата: {analysis.created_at.strftime('%d.%m.%Y')}
"""
        
        summary_content += "\n---\nСгенерировано автоматически"
        
        return summary_content.encode('utf-8')


class ImpulsDataAnalyzer:
    """
    Класс для анализа данных импульса
    """
    
    def __init__(self):
        self.logger = logging.getLogger('celery.module.impuls_analysis.data_analysis')
    
    def analyze_data(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует обработанные данные
        
        Args:
            processed_data: Обработанные данные
            
        Returns:
            Результаты анализа
        """
        self.logger.info("Начало анализа данных импульса")
        
        # TODO: Реализовать алгоритм анализа данных
        # Пока возвращаем заглушку
        
        analysis_results = {
            'analysis_type': 'combined',
            'analysis_completed_at': '2024-01-01T00:00:00Z',
            'results': {
                'force_calculation': self._analyze_force_calculation(
                    processed_data.get('force_calculation', {})
                ),
                'experiment_plan': self._analyze_experiment_plan(
                    processed_data.get('experiment_plan', {})
                ),
            },
            'summary': {
                'total_analyses': len(processed_data),
                'status': 'completed'
            }
        }
        
        self.logger.info("Анализ данных импульса завершен")
        return analysis_results
    
    def _analyze_force_calculation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует данные расчета силы
        
        Args:
            data: Данные расчета силы
            
        Returns:
            Результаты анализа расчета силы
        """
        # TODO: Реализовать анализ расчета силы
        return {
            'analysis_type': 'force_calculation',
            'status': 'analyzed',
            'metrics': {
                'force_range': 'unknown',
                'calculation_accuracy': 'unknown',
            }
        }
    
    def _analyze_experiment_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует данные плана эксперимента
        
        Args:
            data: Данные плана эксперимента
            
        Returns:
            Результаты анализа плана эксперимента
        """
        # TODO: Реализовать анализ плана эксперимента
        return {
            'analysis_type': 'experiment_plan',
            'status': 'analyzed',
            'metrics': {
                'experiment_steps': 0,
                'complexity_level': 'unknown',
            }
        }


def run_protocol_analysis(protocol_number: str, analysis_id: str = None) -> Dict[str, Any]:
	"""
	Выполняет анализ по номеру протокола: строит 2 графика и
	возвращает результаты (пути к изображениям и данные экстремумов).
	Изображения сохраняются в media/impuls_analysis/analyses с UUID-именами.
	"""
	import os  # локальный импорт, чтобы избежать избыточных зависимостей при импорте модуля
	import io
	import numpy as np
	import pandas as pd
	import matplotlib
	matplotlib.use('Agg')
	import matplotlib.pyplot as plt
	from matplotlib.ticker import FuncFormatter
	from django.conf import settings
	from django.core.files.base import ContentFile
	from src.modules.impuls_analysis.models import ImpulsForceRecord, ImpulsPlanRecord

	force_qs = ImpulsForceRecord.objects.filter(protocol_number=protocol_number)
	plan_qs = ImpulsPlanRecord.objects.filter(protocol_number=protocol_number)
	if not force_qs.exists() or not plan_qs.exists():
		raise ValueError('Для указанного протокола должны существовать записи в обеих таблицах: ImpulsForceRecord и ImpulsPlanRecord.')

	force_df = pd.DataFrame(list(force_qs.values('v', 'f', 'pct_static', 'energy_j')))
	if force_df.empty:
		raise ValueError('Не удалось сформировать данные по силе (пустой набор).')

	force_df = force_df[['v', 'f', 'pct_static', 'energy_j']].dropna(subset=['v', 'f']).sort_values('v')
	v = force_df['v'].to_numpy()
	f = force_df['f'].to_numpy()
	p_static = int(round(float(force_df['pct_static'].dropna().mean()))) if force_df['pct_static'].notna().any() else 0
	energy_j = int(round(float(force_df['energy_j'].dropna().mean()))) if force_df['energy_j'].notna().any() else 0

	# Поиск максимумов
	try:
		from scipy.signal import find_peaks  # type: ignore
		peaks, _ = find_peaks(f, prominence=1e-6)
	except Exception:
		dy = np.gradient(f, v)
		s = np.sign(dy)
		peaks = np.where((s[:-1] > 0) & (s[1:] < 0))[0] + 1

	MIN_F = 1000.0
	peaks = peaks[f[peaks] >= MIN_F]
	peaks = peaks[f[peaks] >= 0]

	ON_THR = 1000.0
	OFF_THR = 1000.0
	above_on = f >= ON_THR
	above_off = f >= OFF_THR
	starts = np.where((~above_on[:-1]) & (above_on[1:]))[0] + 1
	stops = np.where((above_off[:-1]) & (~above_off[1:]))[0] + 1
	if len(above_on) > 0 and above_on[0]:
		starts = np.r_[0, starts]
	if len(starts) and len(stops):
		if stops[0] < starts[0]:
			stops = stops[1:]
		if len(starts) > len(stops):
			stops = np.r_[stops, len(f) - 1]
	elif len(starts) and not len(stops):
		stops = np.array([len(f) - 1])
	elif len(stops) and not len(starts):
		starts = np.array([0])
	pulse_windows = [(s_i, e_i) for s_i, e_i in zip(starts, stops) if e_i - s_i > 2]

	fmt_int = FuncFormatter(lambda val, pos: f'{int(val):,}'.replace(',', ' '))

	max_h_used = 0.0
	areas: List[tuple] = []
	pulse_rows: List[Dict[str, Any]] = []
	
	# Подробный график
	plt.figure(figsize=(7, 5))
	plt.plot(v, f, linewidth=1.5, label=f'Pst={p_static}%')
	for k, (i0, i1) in enumerate(pulse_windows, 1):
		plt.fill_between(v[i0:i1 + 1], 0, f[i0:i1 + 1], alpha=0.25)
		h = float(np.max(f[i0:i1 + 1]) + 150000.0)
		max_h_used = max(max_h_used, h)
		plt.vlines(v[i0], 0, h, colors='black', linestyles='--', alpha=0.7)
		plt.vlines(v[i1], 0, h, colors='black', linestyles='--', alpha=0.7)
		xm = (v[i0] + v[i1]) / 2.0
		plt.annotate('', xy=(v[i1], h), xytext=(v[i0], h),
		            arrowprops=dict(arrowstyle='<->', lw=1, color='black', alpha=0.8))
		t_offset = 0.02 * max(float(np.max(f)), 1.0)
		plt.text(xm, h + t_offset, 'T', ha='center', va='bottom', fontsize=10)
		S = float(np.trapz(f[i0:i1 + 1], v[i0:i1 + 1]))
		duration_v = float(v[i1] - v[i0])
		v_start, v_end = float(v[i0]), float(v[i1])
		in_pulse_max = peaks[(peaks >= i0) & (peaks <= i1)]
		for j, p in enumerate(in_pulse_max, 1):
			plt.scatter(v[p], f[p], c='r', s=40)
			plt.annotate(f'F{j}', xy=(v[p], f[p]), xytext=(v[p], f[p] + 50000.0),
			            arrowprops=dict(arrowstyle='->', lw=1), ha='center', fontsize=9)
		areas.append((k, S, xm))
		if len(in_pulse_max) == 0:
			pulse_rows.append({
				'pulse_id': k, 'extremum_id': None, 'extremum_type': None,
				'v': None, 'f': None,
				'duration_v': duration_v, 'area': S,
				'v_start': v_start, 'v_end': v_end,
			})
		else:
			for j, p in enumerate(in_pulse_max, 1):
				pulse_rows.append({
					'pulse_id': k, 'extremum_id': j, 'extremum_type': 'max',
					'v': float(v[p]), 'f': float(f[p]),
					'duration_v': duration_v, 'area': S,
					'v_start': v_start, 'v_end': v_end,
				})
	for k, S, xm in areas:
		plt.text(xm, max(ON_THR * 1.1, float(np.max(f)) * 0.01), f'S{k}', 
           ha='center', va='bottom', fontsize=9)
          
	plt.xlabel('Время, с')
	plt.ylabel('Сила удара, Н')
	plt.title(f'Энергия удара A={energy_j} Дж')
	upper = max(1000000.0, max_h_used * 1.08, float(np.max(f)) * 1.05)
	plt.ylim(0, upper)
	plt.yticks(np.arange(0, 1000001, 100000))
	plt.gca().yaxis.set_major_formatter(fmt_int)
	plt.grid(True, alpha=0.3)
	plt.legend()
	plt.tight_layout()
	
	# Сохранение подробного графика в буфер
	detailed_buffer = io.BytesIO()
	plt.savefig(detailed_buffer, format='png', dpi=150)
	detailed_buffer.seek(0)
	plt.close()

	# Базовый график
	plt.figure(figsize=(7, 5))
	plt.plot(v, f, linewidth=1.5, label=f'Pst={p_static}%')
	plt.xlabel('Время, с')
	plt.ylabel('Сила удара, Н')
	plt.title(f'Энергия удара A={energy_j} Дж')
	plt.ylim(0, 1000000.0)
	plt.yticks(np.arange(0, 1000001, 100000))
	plt.gca().yaxis.set_major_formatter(fmt_int)
	plt.grid(True, alpha=0.3)
	plt.legend()
	plt.tight_layout()
	
	# Сохранение базового графика в буфер
	plain_buffer = io.BytesIO()
	plt.savefig(plain_buffer, format='png', dpi=150)
	plain_buffer.seek(0)
	plt.close()

	# Сохраняем изображения в файловую систему
	from django.conf import settings
	import os
	
	analyses_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'analyses')
	os.makedirs(analyses_dir, exist_ok=True)
	
	detailed_path = os.path.join(analyses_dir, f'{analysis_id}_detailed.png')
	plain_path = os.path.join(analyses_dir, f'{analysis_id}_plain.png')
	
	# Сохраняем файлы
	with open(detailed_path, 'wb') as f:
		f.write(detailed_buffer.getvalue())
	
	with open(plain_path, 'wb') as f:
		f.write(plain_buffer.getvalue())

	return {
		'protocol_number': protocol_number,
		'p_static': p_static,
		'energy_j': energy_j,
		'detailed_image_path': detailed_path,
		'plain_image_path': plain_path,
		'pulse_maxima': pulse_rows,
	}