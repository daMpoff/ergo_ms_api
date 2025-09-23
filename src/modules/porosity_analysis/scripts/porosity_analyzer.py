"""
Основной модуль анализа пористости изображений микроскопии
"""
import os
import cv2
import traceback
from typing import Dict, Any, Optional

# Настройка Matplotlib для работы в фоновом режиме (без GUI)
# ДОЛЖНО БЫТЬ ДО ИМПОРТА matplotlib
import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend

import numpy as np

from src.modules.porosity_analysis.scripts.preprocessing import detect_scale_bar
from src.modules.porosity_analysis.scripts.core_analysis import advanced_porosity_analysis
from src.modules.porosity_analysis.scripts.calculations import (
    calculate_pore_size_distribution,
    calculate_interpore_distances,
    calculate_pore_orientation,
    calculate_pore_shapes
)
from src.modules.porosity_analysis.scripts.visualization import (
    visualize_porosity_analysis_stages,
    visualize_pore_size_distribution,
    visualize_interpore_distances,
    visualize_pore_orientation,
    visualize_pore_shapes
)
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
from src.modules.porosity_analysis.scripts.config import FILES, MESSAGES
from src.modules.porosity_analysis.scripts.utils import calculate_basic_pore_statistics
from src.modules.porosity_analysis.utils import is_cancelled


class PorosityAnalyzer:
    """Главный класс для анализа пористости изображений микроскопии"""
    
    def __init__(self):
        self.config_files = FILES
        self.messages = MESSAGES
        self.last_results = None
    
    def integrated_analysis(
        self, 
        image_path: str, 
        scale_value: float, 
        save_directory: str
    ) -> Optional[Dict[str, Any]]:
        """
        Интегрированный анализ пористости с автоматическим определением масштаба
        
        Args:
            image_path: Путь к изображению
            scale_value: Значение шкалы в микрометрах
            save_directory: Директория для сохранения результатов
            
        Returns:
            Результаты анализа или None в случае ошибки
        """
        try:
            # Ранняя проверка отмены
            analysis_id_env = os.environ.get('POROSITY_ANALYSIS_ID')
            if analysis_id_env and is_cancelled(int(analysis_id_env)):
                print(f"Задача анализа {analysis_id_env} отменена до выполнения. Выход.")
                return None
            # 1. Определение масштаба по линейке
            scale_results = self._detect_scale(image_path, scale_value, save_directory)
            pixels_per_micron, scale_result, scale_region = scale_results
            microns_per_pixel = 1.0 / pixels_per_micron
            
            self._log_scale_detection(pixels_per_micron, microns_per_pixel, scale_region)
            # Больше не сохраняем файл шкалы на диск
            
            # 2. Анализ пористости с учетом масштаба
            # Проверка отмены перед тяжелым этапом
            analysis_id_env = os.environ.get('POROSITY_ANALYSIS_ID')
            if analysis_id_env and is_cancelled(int(analysis_id_env)):
                print(f"Задача анализа {analysis_id_env} отменена перед основным этапом. Выход.")
                return None

            core_results = advanced_porosity_analysis(
                image_path, pixels_per_micron, scale_region, save_directory
            )
            
            # 3. Дополнительные расчеты
            additional_results = self._perform_additional_calculations(
                core_results, microns_per_pixel
            )
            
            # 4. Объединение результатов
            results = {**core_results, **additional_results}
            
            # Добавляем информацию о масштабе
            results['pixels_per_micron'] = pixels_per_micron
            results['microns_per_pixel'] = microns_per_pixel
            
            # 5. Создание визуализаций (с проверкой отмены)
            analysis_id_env = os.environ.get('POROSITY_ANALYSIS_ID')
            if analysis_id_env and is_cancelled(int(analysis_id_env)):
                print(f"Задача анализа {analysis_id_env} отменена перед визуализациями. Выход.")
                return None
            # Формируем изображения для отчета в памяти, без сохранения на диск
            in_memory_images = self._create_visualizations_in_memory(results)
            # Добавляем исходное и изображение со шкалой, если доступны
            try:
                orig_img = Image.open(image_path)
                in_memory_images['original_image'] = orig_img
            except Exception:
                pass
            try:
                if isinstance(scale_result, Image.Image):
                    in_memory_images['image_with_scale'] = scale_result
                else:
                    import numpy as np
                    if hasattr(scale_result, 'shape'):
                        in_memory_images['image_with_scale'] = Image.fromarray(scale_result)
            except Exception:
                pass
            results.update(in_memory_images)
            
            # 6. Вывод итоговых результатов
            self._log_final_results(results)
            
            # Сохраняем результаты для последующего доступа
            self.last_results = results
            
            return results
            
        except Exception as e:
            print(f"Ошибка при анализе изображения: {e}")
            traceback.print_exc()
            return None
    
    def _detect_scale(self, image_path: str, scale_value: float, save_directory: str) -> tuple:
        """Обнаруживает масштаб по линейке"""
        return detect_scale_bar(image_path, scale_value, save_directory)
    
    def _log_scale_detection(
        self, 
        pixels_per_micron: float, 
        microns_per_pixel: float,
        scale_region: tuple
    ) -> None:
        """Логирует результаты детекции масштаба (приглушено для Celery)."""
        pass
    
    def _save_scale_image(self, scale_result: np.ndarray, save_directory: str) -> None:
        """(Отключено) Сохранение изображения линейки на диск больше не используется."""
        return
    
    def _perform_additional_calculations(
        self, 
        core_results: Dict[str, Any], 
        microns_per_pixel: float
    ) -> Dict[str, Any]:
        """Выполняет дополнительные расчеты (без избыточного вывода)."""
        
        pore_properties = core_results['pore_properties']
        pore_diameters_microns = core_results['pore_diameters_microns']
        
        # Группируем расчеты для оптимизации
        calculations = self._create_calculation_tasks(
            pore_properties, pore_diameters_microns, microns_per_pixel
        )
        
        # Выполняем все расчеты
        return self._execute_calculations(calculations)
    
    def _create_calculation_tasks(
        self, 
        pore_properties: list, 
        pore_diameters_microns: list,
        microns_per_pixel: float
    ) -> dict:
        """Создает задачи для расчетов"""
        return {
            'pore_size_distribution': lambda: calculate_pore_size_distribution(
                pore_properties, pore_diameters_microns, microns_per_pixel
            ),
            'interpore_distances_and_centers': lambda: calculate_interpore_distances(
                pore_properties, microns_per_pixel
            ),
            'pore_orientation': lambda: calculate_pore_orientation(
                pore_properties, microns_per_pixel
            ),
            'pore_shapes': lambda: calculate_pore_shapes(
                pore_properties, microns_per_pixel
            )
        }
    
    def _execute_calculations(self, calculations: dict) -> Dict[str, Any]:
        """Выполняет все расчеты"""
        results = {}
        
        # Распределение пор по размерам
        results['pore_size_distribution'] = calculations['pore_size_distribution']()
        
        # Межпоровые расстояния
        interpore_distances, pore_centers = calculations['interpore_distances_and_centers']()
        results['interpore_distances'] = interpore_distances
        results['pore_centers'] = pore_centers
        
        # Ориентация и форма пор
        results['pore_orientation'] = calculations['pore_orientation']()
        results['pore_shapes'] = calculations['pore_shapes']()
        
        return results
    
    def _create_visualizations(self, results: Dict[str, Any], save_directory: str) -> None:
        """(Deprecated) Ранее создавали файлы визуализаций. Не используется."""
        return

    def _create_visualizations_in_memory(self, results: Dict[str, Any]) -> Dict[str, Image.Image]:
        """Генерирует ключевые визуализации и возвращает их как PIL.Image в памяти."""
        images: Dict[str, Image.Image] = {}
        try:
            # Figure 1: gray and enhanced side-by-side
            fig, axs = plt.subplots(1, 2, figsize=(12, 6))
            axs[0].imshow(results['gray'], cmap='gray')
            axs[0].set_title('Исходное изображение')
            axs[0].axis('off')
            axs[1].imshow(results['enhanced'], cmap='gray')
            axs[1].set_title('Улучшение контраста')
            axs[1].axis('off')
            bio = BytesIO()
            fig.tight_layout()
            fig.savefig(bio, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            bio.seek(0)
            images['figure1_contrast'] = Image.open(bio)
        except Exception:
            pass

        try:
            # Figure 4: mask and labeled pores
            fig, axs = plt.subplots(1, 2, figsize=(12, 6))
            axs[0].imshow(results['binary_mask'], cmap='gray')
            axs[0].set_title('Бинарная маска пор')
            axs[0].axis('off')
            import matplotlib.pyplot as _plt
            from skimage import color as _color
            labeled_viz = _color.label2rgb(results['labeled_pores'], bg_label=0)
            axs[1].imshow(labeled_viz)
            axs[1].set_title(f"Определенные поры: {results['number_of_pores']}")
            axs[1].axis('off')
            bio = BytesIO()
            fig.tight_layout()
            fig.savefig(bio, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            bio.seek(0)
            images['figure4_mask_result'] = Image.open(bio)
        except Exception:
            pass

        # Figure 2: исключенные области (линии/аномалии/шкала) и суммарно
        try:
            import numpy as _np
            gray = results['gray']
            lines_exclude_mask = results['lines_exclude_mask']
            anomalies_exclude_mask = results['anomalies_exclude_mask']
            scale_exclude_mask = results['scale_exclude_mask']
            exclude_mask = results['exclude_mask']

            fig, axs = plt.subplots(1, 3, figsize=(18, 6))
            excluded_lines_viz = gray.copy()
            excluded_lines_viz[~lines_exclude_mask] = 255
            axs[0].imshow(excluded_lines_viz, cmap='gray')
            axs[0].set_title(f"Исключенные линии\n({_np.sum(~lines_exclude_mask)} пикселей)")
            axs[0].axis('off')

            excluded_anomalies_viz = gray.copy()
            excluded_anomalies_viz[~anomalies_exclude_mask] = 255
            axs[1].imshow(excluded_anomalies_viz, cmap='gray')
            axs[1].set_title(f"Исключенные аномалии\n({_np.sum(~anomalies_exclude_mask)} пикселей)")
            axs[1].axis('off')

            combined_exclusion = _np.zeros((gray.shape[0], gray.shape[1], 3), dtype=_np.uint8)
            gray_norm = ((gray - gray.min()) / (gray.max() - gray.min()) * 255).astype(_np.uint8)
            combined_exclusion[:, :, 0] = gray_norm
            combined_exclusion[:, :, 1] = gray_norm
            combined_exclusion[:, :, 2] = gray_norm
            lines_mask = ~lines_exclude_mask
            combined_exclusion[lines_mask, 0] = 255
            combined_exclusion[lines_mask, 1] = 0
            combined_exclusion[lines_mask, 2] = 0
            anomalies_only_mask = (~anomalies_exclude_mask) & lines_exclude_mask
            combined_exclusion[anomalies_only_mask, 0] = 0
            combined_exclusion[anomalies_only_mask, 1] = 100
            combined_exclusion[anomalies_only_mask, 2] = 255
            scale_only_mask = (~scale_exclude_mask) & lines_exclude_mask & anomalies_exclude_mask
            combined_exclusion[scale_only_mask, 0] = 255
            combined_exclusion[scale_only_mask, 1] = 255
            combined_exclusion[scale_only_mask, 2] = 0
            axs[2].imshow(combined_exclusion)
            total_excluded = _np.sum(~exclude_mask)
            axs[2].set_title(f"Все исключенные области\nВсего: {total_excluded} пикселей")
            axs[2].axis('off')

            bio = BytesIO()
            fig.tight_layout()
            fig.savefig(bio, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            bio.seek(0)
            images['figure2_excluded_areas'] = Image.open(bio)
        except Exception:
            pass

        # Figure 3: текстурный признак и кластеризация (без сохранения на диск)
        try:
            import numpy as _np
            texture = results['texture']
            segmented = results['segmented']
            exclude_mask = results['exclude_mask']
            fig, axs = plt.subplots(1, 2, figsize=(12, 6))
            texture_viz = texture.copy()
            texture_viz[~exclude_mask] = texture_viz.min()
            axs[0].imshow(texture_viz, cmap='viridis')
            axs[0].set_title('Текстурный признак (энтропия)')
            axs[0].axis('off')
            K = len(_np.unique(segmented))
            cluster_img = _np.zeros_like(segmented, dtype=_np.uint8)
            for i in range(K):
                cluster_img[(segmented == i) & exclude_mask] = 85 * i
            axs[1].imshow(cluster_img, cmap='viridis')
            axs[1].set_title('Результат кластеризации')
            axs[1].axis('off')
            bio = BytesIO()
            fig.tight_layout()
            fig.savefig(bio, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            bio.seek(0)
            images['figure3_texture_clusters'] = Image.open(bio)
        except Exception:
            pass

        try:
            # Figure 5: overlay
            gray = results['gray']
            import numpy as np
            overlay = np.dstack([gray, gray, gray])
            overlay[results['labeled_pores'] > 0, 0] = 255
            overlay[results['labeled_pores'] > 0, 1] = 0
            overlay[results['labeled_pores'] > 0, 2] = 0
            fig, ax = plt.subplots(1, 1, figsize=(6, 6))
            ax.imshow(overlay)
            ax.set_title('Наложение пор на исходное изображение')
            ax.axis('off')
            bio = BytesIO()
            fig.tight_layout()
            fig.savefig(bio, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            bio.seek(0)
            images['figure5_overlay'] = Image.open(bio)
        except Exception:
            pass

        # Дополнительные графики (по возможности)
        try:
            df = results.get('pore_size_distribution')
            if df is not None and hasattr(df, 'empty') and not df.empty:
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.bar(df['Интервал диаметров (мкм)'], df['Количество пор'], color='skyblue', edgecolor='black')
                ax.set_title('Распределение пор по размерам')
                ax.set_xlabel('Диаметр поры (мкм)')
                ax.set_ylabel('Количество пор')
                plt.xticks(rotation=45)
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['pore_size_distribution_fig'] = Image.open(bio)
        except Exception:
            pass

        # Межпоровые расстояния (если точки центров доступны)
        try:
            centers = results.get('pore_centers')
            min_distances = results.get('interpore_distances')
            if centers is not None and min_distances is not None and len(centers) >= 2:
                import numpy as _np
                from scipy.spatial import Voronoi, voronoi_plot_2d
                from scipy.spatial.distance import pdist, squareform
                distances_matrix = squareform(pdist(centers))
                _np.fill_diagonal(distances_matrix, _np.inf)
                fig, ax = plt.subplots(figsize=(12, 12))
                vor = Voronoi(centers)
                voronoi_plot_2d(vor, ax=ax, show_vertices=False, line_colors='gray', line_width=1, line_alpha=0.6)
                ax.plot(centers[:, 1], centers[:, 0], 'ko', markersize=4)
                for i, (y, x) in enumerate(centers):
                    if i < len(min_distances):
                        nearest_idx = _np.argmin(distances_matrix[i])
                        nearest_y, nearest_x = centers[nearest_idx]
                        ax.plot([x, nearest_x], [y, nearest_y], 'r-', alpha=0.5, linewidth=0.8)
                ax.set_title('Межпоровые расстояния и диаграмма Вороного')
                ax.set_xlim(0, _np.max(centers[:, 1]) * 1.1)
                ax.set_ylim(0, _np.max(centers[:, 0]) * 1.1)
                ax.invert_yaxis()
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['interpore_distances_fig'] = Image.open(bio)
        except Exception:
            pass

        # Ориентация пор: роза направлений и гистограмма
        try:
            orientation_data = results.get('pore_orientation')
            if orientation_data:
                import numpy as _np
                orientations = orientation_data['orientations']
                filtered_properties = orientation_data['filtered_properties']
                mean_orientation_deg = orientation_data['mean_orientation']
                std_orientation_deg = orientation_data['std_orientation']
                R = orientation_data['orientation_strength']
                has_preferred_direction = orientation_data['has_preferred_direction']
                # Роза направлений
                fig = plt.figure(figsize=(12, 12))
                ax = fig.add_subplot(111, projection='polar')
                orientations_rad = _np.radians(orientations)
                bins = _np.linspace(0, _np.pi, 19)
                hist, bin_edges = _np.histogram(orientations_rad, bins=bins)
                hist = _np.concatenate([hist, hist])
                theta = _np.linspace(0, 2*_np.pi, 36, endpoint=False)
                ax.bar(theta, hist, width=_np.pi/18, bottom=0.0, alpha=0.7)
                ax.set_title('Роза направлений пор', pad=20)
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['pore_orientation_rose_fig'] = Image.open(bio)

                # Взвешенная гистограмма
                fig, ax = plt.subplots(figsize=(10, 6))
                weights = [prop['area'] for prop in filtered_properties]
                hist2, bin_edges = _np.histogram(orientations, bins=18, range=(0, 180), weights=weights)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                ax.bar(bin_centers, hist2, width=180/18, alpha=0.7, color='skyblue', edgecolor='black')
                ax.set_xlabel('Угол ориентации (°)')
                ax.set_ylabel('Суммарная площадь пор (мкм²)')
                ax.set_title('Распределение ориентации пор, взвешенное по площади')
                ax.set_xlim(0, 180)
                ax.set_xticks(_np.linspace(0, 180, 7))
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['pore_orientation_hist_fig'] = Image.open(bio)
        except Exception:
            pass

        # Формы пор: композит и распределения
        try:
            shapes_df = results.get('pore_shapes')
            if shapes_df is not None and hasattr(shapes_df, 'empty') and not shapes_df.empty:
                import matplotlib.colors as _mcolors
                from matplotlib.patches import Ellipse as _Ellipse
                from matplotlib.lines import Line2D as _Line2D
                import numpy as _np
                shape_counts = shapes_df['Тип формы'].value_counts()
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
                shape_counts.plot.pie(autopct='%1.1f%%', ax=ax1, startangle=90,
                                      colors=[_mcolors.CSS4_COLORS[c] for c in ['royalblue','forestgreen','darkorange','crimson','purple']])
                ax1.set_title('Распределение форм пор')
                ax1.set_ylabel('')
                max_x = shapes_df['Центроид X'].max() * 1.1 if not shapes_df.empty else 100
                max_y = shapes_df['Центроид Y'].max() * 1.1 if not shapes_df.empty else 100
                ax2.set_xlim(0, max_x)
                ax2.set_ylim(0, max_y)
                color_map = {
                    'Круглая': 'royalblue',
                    'Овальная': 'forestgreen',
                    'Удлиненная': 'darkorange',
                    'Линейная': 'crimson',
                    'Неправильная': 'purple'
                }
                for _, row in shapes_df.iterrows():
                    if (row['Эллиптичность'] > 0 and row['Площадь (мкм²)'] > 0 and 
                        not _np.isnan(row['Эллиптичность']) and not _np.isnan(row['Площадь (мкм²)'])):
                        width = _np.sqrt(row['Площадь (мкм²)'] / (_np.pi * row['Эллиптичность']))
                        height = width * row['Эллиптичность']
                        ellipse = _Ellipse((row['Центроид X'], row['Центроид Y']), width=width*2, height=height*2,
                                          angle=_np.degrees(row['Ориентация']), facecolor=color_map.get(row['Тип формы'], 'gray'),
                                          alpha=0.5, edgecolor='black', linewidth=0.5)
                        ax2.add_patch(ellipse)
                    else:
                        ax2.plot(row['Центроид X'], row['Центроид Y'], 'o', color=color_map.get(row['Тип формы'], 'gray'), markersize=3, alpha=0.7)
                legend_elements = [
                    _Line2D([0],[0], marker='o', color='w', markerfacecolor=color, label=shape, markersize=10)
                    for shape, color in color_map.items() if shape in shape_counts.index
                ]
                ax2.legend(handles=legend_elements, loc='upper right')
                ax2.set_title('Визуализация форм пор')
                ax2.set_xlabel('X (мкм)')
                ax2.set_ylabel('Y (мкм)')
                ax2.invert_yaxis()
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['pore_shapes_analysis_fig'] = Image.open(bio)

                # Гистограмма кругового фактора
                fig, ax = plt.subplots(figsize=(10,6))
                ax.hist(shapes_df['Круговой фактор'], bins=20, color='skyblue', edgecolor='black')
                ax.set_title('Распределение кругового фактора пор')
                ax.set_xlabel('Круговой фактор')
                ax.set_ylabel('Количество пор')
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['circularity_distribution_fig'] = Image.open(bio)

                # Эллиптичность vs площадь
                fig, ax = plt.subplots(figsize=(10,6))
                ax.scatter(shapes_df['Площадь (мкм²)'], shapes_df['Эллиптичность'], alpha=0.7, edgecolor='black')
                ax.set_xscale('log')
                ax.set_title('Зависимость эллиптичности от площади пор')
                ax.set_xlabel('Площадь (мкм²)')
                ax.set_ylabel('Эллиптичность')
                fig.tight_layout()
                bio = BytesIO()
                fig.savefig(bio, format='png', dpi=300)
                plt.close(fig)
                bio.seek(0)
                images['ellipticity_vs_area_fig'] = Image.open(bio)
        except Exception:
            pass

        return images
    
    def _create_visualization_tasks(
        self, 
        results: Dict[str, Any], 
        save_directory: str
    ) -> list:
        """Создает задачи для визуализации"""
        return [
            # Основные этапы анализа
            lambda: visualize_porosity_analysis_stages(
                results['gray'], results['enhanced'], results['texture'], 
                results['segmented'], results['binary_mask'], results['labeled_pores'],
                results['scale_region'], results['porosity_percentage'], results['number_of_pores'],
                results['exclude_mask'], results['lines_exclude_mask'], 
                results['anomalies_exclude_mask'], results['scale_exclude_mask'], save_directory
            ),
            # Остальные визуализации
            lambda: visualize_pore_size_distribution(
                results['pore_size_distribution'], save_directory
            ),
            lambda: visualize_interpore_distances(
                results['interpore_distances'], results['pore_centers'], 
                1.0 / results.get('pixels_per_micron', 1), save_directory
            ),
            lambda: visualize_pore_orientation(
                results['pore_orientation'], save_directory
            ),
            lambda: visualize_pore_shapes(
                results['pore_shapes'], save_directory
            )
        ]
    
    def _log_final_results(self, results: Dict[str, Any]) -> None:
        """Выводит итоговые результаты анализа (приглушено для Celery)."""
        return
        
        # Основные метрики
        self._log_main_metrics(results)
        
        # Информация об исключенных областях
        self._log_excluded_areas(results)
    
    def _log_main_metrics(self, results: Dict[str, Any]) -> None:
        """Логирует основные метрики (приглушено)."""
        return
    
    def _log_excluded_areas(self, results: Dict[str, Any]) -> None:
        """Логирует информацию об исключенных областях"""
        total_pixels = results['gray'].size
        
        # Подсчет исключенных областей
        scale_excluded = np.sum(~results['scale_exclude_mask'])
        lines_excluded = np.sum(~results['lines_exclude_mask'])
        anomalies_excluded = np.sum(~results['anomalies_exclude_mask'])
        total_excluded = np.sum(~results['exclude_mask'])
        
        # Приглушаем подробные распечатки
        return
    
    def get_last_results(self):
        """Возвращает результаты последнего анализа"""
        return self.last_results


# Функция обратной совместимости
def integrated_analysis(image_path: str, scale_value: float, save_directory: str) -> Optional[Dict[str, Any]]:
    """
    Функция обратной совместимости для интегрированного анализа пористости
    
    Args:
        image_path: Путь к изображению
        scale_value: Значение шкалы в микрометрах
        save_directory: Директория для сохранения результатов
        
    Returns:
        Результаты анализа
    """
    analyzer = PorosityAnalyzer()
    return analyzer.integrated_analysis(image_path, scale_value, save_directory) 