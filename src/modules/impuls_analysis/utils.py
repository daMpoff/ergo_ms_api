"""
Утилиты для модуля анализа импульса.
Обработка Excel файлов и генерация протоколов.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

from .models import ImpulsAnalysis

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
            print(ws.title)
            sheet_title: str = ws.title or ''

            # Из названия листа извлекаем число до пробела (например, "25 Дж" -> 25)
            sheet_energy_value: Optional[float] = None
            m = re.search(r"(-?\d+(?:[\.,]\d+)?)", sheet_title)
            if m:
                try:
                    sheet_energy_value = float(m.group(1).replace(',', '.'))
                except ValueError:
                    sheet_energy_value = None

            # Общие значения для листа
            energy_j = self._get_numeric(ws, 'C5')  # Энергия удара, Дж
            velocity_ms = self._get_numeric(ws, 'D5')  # Скорость удара, м/с
            force_n = self._get_numeric(ws, 'E5')  # Сила удара (P), Н

            # Сканируем протоколы: номера в G2, K2, O2, ... (через каждые 3 столбца)
            # Соответствующие проценты: G4, K4, O4, ...
            # Блок данных для каждого протокола: 3 столбца, начиная с F, пропуск 1 столбца, затем J, ...
            protocol_header_cols = self._iter_cols(start_col='G', step=4)  # G,K,O,...
            data_block_start_cols = self._iter_cols(start_col='F', step=4)  # F,J,N,...

            protocols: List[Dict[str, Any]] = []

            for (hdr_col_letter, data_col_letter) in zip(protocol_header_cols, data_block_start_cols):
                # Ограничим количество итераций, чтобы не уйти в бесконечный цикл: максимум 100 блоков
                if len(protocols) >= 100:
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

                # Заголовки ожидаются на строке 5 для двух последних столбцов, время с 6-й строки
                # Данные идут построчно до первой полностью пустой тройки ячеек
                rows: List[Dict[str, Optional[float]]] = []
                row_idx = 6
                empty_rows = 0
                max_empty_rows = 50  # страховка на случай редких пустых вставок

                while True:
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
                'sheet_title': sheet_title,
                'sheet_energy_value': sheet_energy_value,
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
Тип анализа: {analysis.get_analysis_type_display()}
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
   Тип: {analysis.get_analysis_type_display()}
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
