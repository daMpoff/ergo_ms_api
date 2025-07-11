#!/usr/bin/env python3
"""
Главный скрипт для анализа пористости изображений микроскопии

Использование:
    python main.py

Настройки можно изменить в переменных ниже.
"""
import os
import sys

# Настройка Matplotlib для работы в фоновом режиме (без GUI)
# ДОЛЖНО БЫТЬ ДО ИМПОРТА matplotlib
import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend

from pathlib import Path
from typing import Optional

from src.modules.porosity_analysis.scripts.porosity_analyzer import PorosityAnalyzer


def run_analysis(config):
    """
    Функция для запуска анализа пористости с конфигурацией
    
    Args:
        config: Объект конфигурации с параметрами анализа
        
    Returns:
        dict: Результаты анализа или None в случае ошибки
    """
    try:
        app = PorosityAnalysisApp()
        
        # Запускаем анализ с параметрами из конфигурации
        results = app.run_analysis(
            save_directory=config.output_directory,
            image_path=config.input_image_path,  # Передаем полный путь к изображению
            scale_value=config.scale_value
        )
        
        if results:
            # Логируем исходные результаты для отладки
            print(f"Исходные результаты анализа: {results}")
            
            # Возвращаем результаты анализа
            final_results = {
                'porosity_percentage': results.get('porosity_percentage', 0.0),
                'number_of_pores': results.get('number_of_pores', 0),
                'mean_pore_size_microns': results.get('mean_pore_size_microns', 0.0),
                'max_pore_size_microns': results.get('max_pore_size_microns', 0.0),
                'min_pore_size_microns': results.get('min_pore_size_microns', 0.0),
                'pore_density': results.get('pore_density', 0.0),
                'average_interpore_distance': results.get('average_interpore_distance', 0.0)
            }
            
            print(f"Финальные результаты: {final_results}")
            return final_results
        else:
            return None
            
    except Exception as e:
        print(f"Ошибка при выполнении анализа: {e}")
        return None


class PorosityAnalysisApp:
    """Главное приложение для анализа пористости"""
    
    def __init__(self):
        self.analyzer = PorosityAnalyzer()
        self.default_config = {
            'save_directory': "data",
            'image_path': "image.png",
            'scale_value': 100,  # микрометры
        }
    
    def run_analysis(
        self, 
        save_directory: Optional[str] = None,
        image_path: Optional[str] = None,
        scale_value: Optional[float] = None
    ) -> bool:
        """
        Запускает анализ пористости с заданными параметрами
        
        Args:
            save_directory: Путь к папке с файлами
            image_path: Полный путь к изображению
            scale_value: Значение шкалы в микрометрах
            
        Returns:
            True если анализ прошел успешно, False в противном случае
        """
        # Использование значений по умолчанию
        if save_directory is None:
            save_directory = self.default_config['save_directory']
        if image_path is None:
            image_path = self.default_config['image_path']
        if scale_value is None:
            scale_value = self.default_config['scale_value']
        
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
        return results if success else None
    
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
            image_path="image.png",        # Имя файла изображения
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