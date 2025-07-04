#!/usr/bin/env python3
"""
Главный скрипт для анализа пористости изображений микроскопии

Использование:
    python main.py

Настройки можно изменить в переменных ниже.
"""
import os
import sys

from pathlib import Path
from typing import Optional

from src.external.analysis_porosity.square_porosity.porosity_analyzer import PorosityAnalyzer


class PorosityAnalysisApp:
    """Главное приложение для анализа пористости"""
    
    def __init__(self):
        self.analyzer = PorosityAnalyzer()
        self.default_config = {
            'save_directory': "analysed_data_1",
            'image_filename': "image.png",
            'scale_value': 100,  # микрометры
        }
    
    def run_analysis(
        self, 
        save_directory: Optional[str] = None,
        image_filename: Optional[str] = None,
        scale_value: Optional[float] = None
    ) -> bool:
        """
        Запускает анализ пористости с заданными параметрами
        
        Args:
            save_directory: Путь к папке с файлами
            image_filename: Имя файла изображения
            scale_value: Значение шкалы в микрометрах
            
        Returns:
            True если анализ прошел успешно, False в противном случае
        """
        # Использование значений по умолчанию
        if save_directory is None:
            save_directory = self.default_config['save_directory']
        if image_filename is None:
            image_filename = self.default_config['image_filename']
        if scale_value is None:
            scale_value = self.default_config['scale_value']
        
        image_path = os.path.join(save_directory, image_filename)
        
        # Вывод информации о запуске
        self._print_startup_info(image_path, scale_value, save_directory)
        
        # Проверка существования файлов
        if not self._validate_inputs(image_path, save_directory):
            return False
        
        # Запуск анализа
        print("Начинаем анализ пористости...")
        results = self.analyzer.integrated_analysis(image_path, scale_value, save_directory)
        
        # Обработка результатов
        success = self._handle_results(results, save_directory)
        return success
    
    def _print_startup_info(self, image_path: str, scale_value: float, save_directory: str) -> None:
        """Выводит информацию о запуске анализа"""
        print("=== АНАЛИЗ ПОРИСТОСТИ ИЗОБРАЖЕНИЙ ===")
        print(f"Путь к изображению: {image_path}")
        print(f"Значение шкалы: {scale_value} мкм")
        print(f"Папка для сохранения результатов: {save_directory}")
        print("=" * 40)
    
    def _validate_inputs(self, image_path: str, save_directory: str) -> bool:
        """Проверяет входные данные"""
        # Проверка существования изображения
        if not os.path.exists(image_path):
            print(f"ОШИБКА: Файл изображения не найден: {image_path}")
            return False
        
        # Создание директории для результатов если не существует
        if not os.path.exists(save_directory):
            print(f"Создание директории для результатов: {save_directory}")
            os.makedirs(save_directory, exist_ok=True)
        
        return True
    
    def _handle_results(self, results: Optional[dict], save_directory: str) -> bool:
        """Обрабатывает результаты анализа"""
        if results is not None:
            self._print_success_message(save_directory)
            return True
        else:
            self._print_error_message()
            return False
    
    def _print_success_message(self, save_directory: str) -> None:
        """Выводит сообщение об успешном завершении"""
        print("\n" + "=" * 40)
        print("АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 40)
        print(f"Результаты сохранены в папке: {save_directory}")
        print("Созданы следующие файлы:")
        
        # Список созданных файлов
        output_files = [
            "image_with_scale_bar.png (изображение с обнаруженной шкалой)",
            "scale_bar.png (область шкалы)",
            "figure1_contrast.png (этапы обработки контраста)",
            "figure2_excluded_areas.png (исключенные области)",
            "figure3_texture_clusters.png (текстурный анализ)",
            "figure4_mask_result.png (бинарная маска и результат)",
            "figure5_overlay.png (наложение результатов)",
            "pore_size_distribution.png (распределение размеров пор)",
            "interpore_distances.png (межпоровые расстояния)",
            "pore_orientation_rose.png (роза направлений)",
            "pore_orientation_histogram.png (гистограмма ориентации)",
            "pore_shapes_analysis.png (анализ форм пор)",
            "circularity_distribution.png (распределение кругового фактора)",
            "ellipticity_vs_area.png (эллиптичность vs площадь)"
        ]
        
        for file_desc in output_files:
            print(f"  - {file_desc}")
    
    def _print_error_message(self) -> None:
        """Выводит сообщение об ошибке"""
        print("\n" + "=" * 40)
        print("АНАЛИЗ ЗАВЕРШЕН С ОШИБКОЙ!")
        print("=" * 40)
        print("Проверьте сообщения об ошибках выше.")


def main():
    """Главная функция для запуска анализа пористости"""
    try:
        app = PorosityAnalysisApp()
        
        # Запуск анализа с параметрами по умолчанию
        # Можно изменить параметры здесь:
        success = app.run_analysis(
            save_directory="data",  # Путь к папке с файлами
            image_filename="image.png",        # Имя файла изображения
            scale_value=100                    # Значение шкалы в микрометрах
        )
        
        # Завершение программы с соответствующим кодом
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nАнализ прерван пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 