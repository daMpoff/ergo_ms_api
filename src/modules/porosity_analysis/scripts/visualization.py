import os

# Настройка Matplotlib для работы в фоновом режиме (без GUI)
import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Ellipse
from matplotlib.lines import Line2D

from scipy.spatial import Voronoi, voronoi_plot_2d
from scipy.spatial.distance import pdist, squareform

from skimage import color

def visualize_pore_size_distribution(df, save_directory):
    """Создает визуализацию распределения пор по размерам."""
    if df.empty:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(df['Интервал диаметров (мкм)'], df['Количество пор'], color='skyblue', edgecolor='black')
    ax.set_title('Распределение пор по размерам')
    ax.set_xlabel('Диаметр поры (мкм)')
    ax.set_ylabel('Количество пор')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_path = os.path.join(save_directory, 'pore_size_distribution.png')
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

def visualize_interpore_distances(min_distances_microns, centers, microns_per_pixel, save_directory):
    """Создает визуализацию межпоровых расстояний."""
    if min_distances_microns is None or len(centers) < 2:
        return
    
    distances_matrix = squareform(pdist(centers))
    np.fill_diagonal(distances_matrix, np.inf)
    
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Диаграмма Вороного
    vor = Voronoi(centers)
    voronoi_plot_2d(vor, ax=ax, show_vertices=False, line_colors='gray', line_width=1, line_alpha=0.6)
    
    # Центры пор
    ax.plot(centers[:, 1], centers[:, 0], 'ko', markersize=4)
    
    # Минимальные расстояния
    for i, (y, x) in enumerate(centers):
        if i < len(min_distances_microns):
            nearest_idx = np.argmin(distances_matrix[i])
            nearest_y, nearest_x = centers[nearest_idx]
            
            ax.plot([x, nearest_x], [y, nearest_y], 'r-', alpha=0.5, linewidth=0.8)
            
            mid_x = (x + nearest_x) / 2
            mid_y = (y + nearest_y) / 2
            ax.text(mid_x, mid_y, f"{min_distances_microns[i]:.2f}", fontsize=8, 
                    ha='center', va='center', backgroundcolor='white', alpha=0.7)
    
    ax.set_title('Межпоровые расстояния и диаграмма Вороного')
    ax.set_xlim(0, np.max(centers[:, 1]) * 1.1)
    ax.set_ylim(0, np.max(centers[:, 0]) * 1.1)
    ax.invert_yaxis()
    
    # Статистика
    ax.text(0.02, 0.02, 
            f"Среднее расстояние: {np.mean(min_distances_microns):.2f} мкм\n"
            f"Медианное расстояние: {np.median(min_distances_microns):.2f} мкм\n"
            f"Мин. расстояние: {np.min(min_distances_microns):.2f} мкм\n"
            f"Макс. расстояние: {np.max(min_distances_microns):.2f} мкм",
            transform=ax.transAxes, bbox=dict(facecolor='white', alpha=0.8),
            fontsize=10)
    
    plt.tight_layout()
    output_path = os.path.join(save_directory, 'interpore_distances.png')
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

def visualize_pore_orientation(orientation_data, save_directory):
    """Создает визуализацию ориентации пор."""
    if orientation_data is None:
        return
    
    orientations = orientation_data['orientations']
    filtered_properties = orientation_data['filtered_properties']
    mean_orientation_deg = orientation_data['mean_orientation']
    std_orientation_deg = orientation_data['std_orientation']
    R = orientation_data['orientation_strength']
    has_preferred_direction = orientation_data['has_preferred_direction']
    
    # Роза направлений
    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(111, projection='polar')
    
    orientations_rad = np.radians(orientations)
    bins = np.linspace(0, np.pi, 19)
    hist, bin_edges = np.histogram(orientations_rad, bins=bins)
    
    # Дублирование для полной окружности
    hist = np.concatenate([hist, hist])
    theta = np.linspace(0, 2*np.pi, 36, endpoint=False)
    
    bars = ax.bar(theta, hist, width=np.pi/18, bottom=0.0, alpha=0.7)
    
    # Среднее направление
    if has_preferred_direction:
        mean_theta = np.radians(mean_orientation_deg)
        mean_theta_opposite = (mean_theta + np.pi) % (2 * np.pi)
        ax.arrow(mean_theta, 0, 0, max(hist) * 0.9, alpha=0.8, width=0.05, 
                 edgecolor='red', facecolor='red', lw=2, zorder=5)
        ax.arrow(mean_theta_opposite, 0, 0, max(hist) * 0.9, alpha=0.8, width=0.05, 
                 edgecolor='red', facecolor='red', lw=2, zorder=5)
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_xticks(np.linspace(0, 2 * np.pi, 8, endpoint=False))
    ax.set_xticklabels(['0°', '45°', '90°', '135°', '180°', '225°', '270°', '315°'])
    
    if has_preferred_direction:
        title = f"Роза направлений пор\nСреднее направление: {mean_orientation_deg:.1f}° ± {std_orientation_deg:.1f}°\nСила направленности: {R:.2f} (значительная)"
    else:
        title = f"Роза направлений пор\nНет выраженного предпочтительного направления\nСила направленности: {R:.2f} (слабая)"
    
    ax.set_title(title, pad=20)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_directory, 'pore_orientation_rose.png'), dpi=300)
    plt.close(fig)
    
    # Взвешенная гистограмма
    fig, ax = plt.subplots(figsize=(10, 6))
    
    weights = [prop['area'] for prop in filtered_properties]
    hist, bin_edges = np.histogram(orientations, bins=18, range=(0, 180), weights=weights)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    ax.bar(bin_centers, hist, width=180/18, alpha=0.7, color='skyblue', edgecolor='black')
    
    if has_preferred_direction:
        ax.axvline(x=mean_orientation_deg, color='r', linestyle='--', 
                  linewidth=2, label=f'Среднее: {mean_orientation_deg:.1f}°')
        ax.axvspan(mean_orientation_deg - std_orientation_deg, 
                  mean_orientation_deg + std_orientation_deg, 
                  alpha=0.2, color='red', label=f'СКО: ±{std_orientation_deg:.1f}°')
    
    ax.set_xlabel('Угол ориентации (°)')
    ax.set_ylabel('Суммарная площадь пор (мкм²)')
    ax.set_title('Распределение ориентации пор, взвешенное по площади')
    ax.set_xlim(0, 180)
    ax.set_xticks(np.linspace(0, 180, 7))
    ax.grid(True, alpha=0.3)
    
    if has_preferred_direction:
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_directory, 'pore_orientation_histogram.png'), dpi=300)
    plt.close(fig)

def visualize_pore_shapes(df, save_directory):
    """Создает визуализацию форм пор."""
    if df.empty:
        return
    
    shape_counts = df['Тип формы'].value_counts()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    
    # Круговая диаграмма
    shape_counts.plot.pie(autopct='%1.1f%%', ax=ax1, startangle=90, 
                         colors=[mcolors.CSS4_COLORS[c] for c in 
                                ['royalblue', 'forestgreen', 'darkorange', 'crimson', 'purple']])
    ax1.set_title('Распределение форм пор')
    ax1.set_ylabel('')
    
    # Визуализация эллипсов
    max_x = df['Центроид X'].max() * 1.1 if not df.empty else 100
    max_y = df['Центроид Y'].max() * 1.1 if not df.empty else 100
    
    ax2.set_xlim(0, max_x)
    ax2.set_ylim(0, max_y)
    
    color_map = {
        'Круглая': 'royalblue',
        'Овальная': 'forestgreen',
        'Удлиненная': 'darkorange',
        'Линейная': 'crimson',
        'Неправильная': 'purple',
        'Неопределенная': 'gray'
    }
    
    # Рисование эллипсов
    for _, row in df.iterrows():
        if (row['Эллиптичность'] > 0 and row['Площадь (мкм²)'] > 0 and 
            not np.isnan(row['Эллиптичность']) and not np.isnan(row['Площадь (мкм²)'])):
            
            width = np.sqrt(row['Площадь (мкм²)'] / (np.pi * row['Эллиптичность']))
            height = width * row['Эллиптичность']
            
            ellipse = Ellipse(
                (row['Центроид X'], row['Центроид Y']),
                width=width * 2,
                height=height * 2,
                angle=np.degrees(row['Ориентация']),
                facecolor=color_map.get(row['Тип формы'], 'gray'),
                alpha=0.5,
                edgecolor='black',
                linewidth=0.5
            )
            ax2.add_patch(ellipse)
        else:
            ax2.plot(row['Центроид X'], row['Центроид Y'], 'o', 
                    color=color_map.get(row['Тип формы'], 'gray'), markersize=3, alpha=0.7)
    
    # Легенда
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=color, label=shape, markersize=10)
        for shape, color in color_map.items() if shape in shape_counts.index
    ]
    ax2.legend(handles=legend_elements, loc='upper right')
    
    ax2.set_title('Визуализация форм пор')
    ax2.set_xlabel('X (мкм)')
    ax2.set_ylabel('Y (мкм)')
    ax2.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_directory, 'pore_shapes_analysis.png'), dpi=300)
    plt.close(fig)
    
    # Гистограмма кругового фактора
    plt.figure(figsize=(10, 6))
    plt.hist(df['Круговой фактор'], bins=20, color='skyblue', edgecolor='black')
    plt.title('Распределение кругового фактора пор')
    plt.xlabel('Круговой фактор')
    plt.ylabel('Количество пор')
    plt.axvline(x=0.85, color='r', linestyle='--', label='Граница круглых пор')
    plt.axvline(x=0.65, color='g', linestyle='--', label='Граница овальных пор')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_directory, 'circularity_distribution.png'), dpi=300)
    plt.close()
    
    # Точечная диаграмма
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(df['Площадь (мкм²)'], df['Эллиптичность'], 
                         c=[color_map.get(t, 'gray') for t in df['Тип формы']], 
                         alpha=0.7, edgecolor='black')
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=color, label=shape, markersize=10)
        for shape, color in color_map.items() if shape in df['Тип формы'].values
    ]
    plt.legend(handles=legend_elements)
    
    plt.title('Зависимость эллиптичности от площади пор')
    plt.xlabel('Площадь (мкм²)')
    plt.ylabel('Эллиптичность')
    plt.xscale('log')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_directory, 'ellipticity_vs_area.png'), dpi=300)
    plt.close()

def visualize_porosity_analysis_stages(gray, enhanced, texture, segmented, cleaned_mask, 
                                     labeled_pores, scale_region, porosity, num_pores, 
                                     exclude_mask, lines_exclude_mask, anomalies_exclude_mask, 
                                     scale_exclude_mask, save_directory):
    """Создает визуализацию этапов анализа пористости с исключенными областями."""
    fig_params = {
        'figsize': (12, 6),
        'tight_layout': {'pad': 1.0, 'h_pad': 0.5, 'w_pad': 0.5},
        'subplot_adjust': {'bottom': 0.05, 'top': 0.95}
    }

    # Первый рисунок: исходное изображение и улучшенный контраст
    plt.figure(figsize=fig_params['figsize'])

    plt.subplot(1, 2, 1)
    plt.imshow(gray, cmap='gray')
    plt.title('Исходное изображение', pad=5)
    if scale_region:
        sx, sy, sw, sh = scale_region
        rect = plt.Rectangle((sx, sy), sw, sh, 
                            linewidth=2, edgecolor='r', facecolor='none')
        plt.gca().add_patch(rect)
    plt.axis('off')

    plt.subplot(1, 2, 2)
    plt.imshow(enhanced, cmap='gray')
    plt.title('Улучшение контраста', pad=5)
    plt.axis('off')

    plt.subplots_adjust(**fig_params['subplot_adjust'])
    plt.tight_layout(**fig_params['tight_layout'])
    plt.savefig(os.path.join(save_directory, 'figure1_contrast.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # Второй рисунок: исключенные области
    plt.figure(figsize=(18, 6))

    plt.subplot(1, 3, 1)
    # Улучшенная визуализация исключенных линий
    excluded_lines_viz = gray.copy()
    excluded_lines_viz[~lines_exclude_mask] = 255  # Белым показываем исключенные линии
    plt.imshow(excluded_lines_viz, cmap='gray')
    plt.title(f'Исключенные линии\n({np.sum(~lines_exclude_mask)} пикселей, {(np.sum(~lines_exclude_mask)/gray.size)*100:.2f}%)', pad=5)
    plt.axis('off')

    plt.subplot(1, 3, 2)
    excluded_anomalies_viz = gray.copy()
    excluded_anomalies_viz[~anomalies_exclude_mask] = 255
    plt.imshow(excluded_anomalies_viz, cmap='gray')
    plt.title(f'Исключенные аномалии\n({np.sum(~anomalies_exclude_mask)} пикселей, {(np.sum(~anomalies_exclude_mask)/gray.size)*100:.2f}%)', pad=5)
    plt.axis('off')

    plt.subplot(1, 3, 3)
    # Более контрастная комбинированная визуализация всех исключений
    combined_exclusion = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.uint8)
    
    # Базовое изображение в оттенках серого
    gray_normalized = ((gray - gray.min()) / (gray.max() - gray.min()) * 255).astype(np.uint8)
    combined_exclusion[:, :, 0] = gray_normalized
    combined_exclusion[:, :, 1] = gray_normalized  
    combined_exclusion[:, :, 2] = gray_normalized
    
    # Ярко-красным отмечаем исключенные линии
    lines_mask = ~lines_exclude_mask
    combined_exclusion[lines_mask, 0] = 255
    combined_exclusion[lines_mask, 1] = 0
    combined_exclusion[lines_mask, 2] = 0
    
    # Ярко-синим отмечаем исключенные аномалии (только там где нет линий)
    anomalies_only_mask = (~anomalies_exclude_mask) & lines_exclude_mask
    combined_exclusion[anomalies_only_mask, 0] = 0
    combined_exclusion[anomalies_only_mask, 1] = 100
    combined_exclusion[anomalies_only_mask, 2] = 255
    
    # Желтым отмечаем область шкалы (только там где нет линий и аномалий)
    scale_only_mask = (~scale_exclude_mask) & lines_exclude_mask & anomalies_exclude_mask
    combined_exclusion[scale_only_mask, 0] = 255
    combined_exclusion[scale_only_mask, 1] = 255
    combined_exclusion[scale_only_mask, 2] = 0
    
    plt.imshow(combined_exclusion)
    total_excluded = np.sum(~exclude_mask)
    plt.title(f'Все исключенные области\n(красный=линии, синий=аномалии, желтый=шкала)\nВсего: {total_excluded} пикселей ({(total_excluded/gray.size)*100:.2f}%)', pad=5)
    plt.axis('off')

    plt.subplots_adjust(**fig_params['subplot_adjust'])
    plt.tight_layout(**fig_params['tight_layout'])
    plt.savefig(os.path.join(save_directory, 'figure2_excluded_areas.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # Третий рисунок: текстурный признак и кластеризация
    plt.figure(figsize=fig_params['figsize'])

    plt.subplot(1, 2, 1)
    texture_viz = texture.copy()
    texture_viz[~exclude_mask] = texture_viz.min()  # Затемняем исключенные области
    plt.imshow(texture_viz, cmap='viridis')
    plt.title('Текстурный признак (энтропия)', pad=5)
    plt.axis('off')

    plt.subplot(1, 2, 2)
    K = len(np.unique(segmented))
    cluster_img = np.zeros_like(segmented, dtype=np.uint8)
    for i in range(K):
        cluster_img[(segmented == i) & exclude_mask] = 85 * i
    plt.imshow(cluster_img, cmap='viridis')
    plt.title('Результат кластеризации', pad=5)
    plt.axis('off')

    plt.subplots_adjust(**fig_params['subplot_adjust'])
    plt.tight_layout(**fig_params['tight_layout'])
    plt.savefig(os.path.join(save_directory, 'figure3_texture_clusters.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # Четвертый рисунок: бинарная маска и финальный результат
    plt.figure(figsize=fig_params['figsize'])

    plt.subplot(1, 2, 1)
    plt.imshow(cleaned_mask, cmap='gray')
    plt.title('Бинарная маска пор', pad=5)
    plt.axis('off')

    plt.subplot(1, 2, 2)
    labeled_viz = color.label2rgb(labeled_pores, bg_label=0)
    plt.imshow(labeled_viz)
    plt.title(f'Определенные поры: {num_pores}, Пористость: {porosity:.2f}%', pad=5)
    plt.axis('off')

    plt.subplots_adjust(**fig_params['subplot_adjust'])
    plt.tight_layout(**fig_params['tight_layout'])
    plt.savefig(os.path.join(save_directory, 'figure4_mask_result.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # Пятый рисунок: наложение
    plt.figure(figsize=fig_params['figsize'])

    plt.subplot(1, 2, 1)
    plt.imshow(gray, cmap='gray')
    plt.title('Исходное изображение', pad=5)
    plt.axis('off')

    plt.subplot(1, 2, 2)
    overlay = np.dstack([gray, gray, gray])
    overlay[labeled_pores > 0, 0] = 255
    overlay[labeled_pores > 0, 1] = 0
    overlay[labeled_pores > 0, 2] = 0
    
    # Отмечаем исключенные области полупрозрачным синим
    overlay[~exclude_mask, 2] = np.minimum(overlay[~exclude_mask, 2] + 100, 255)
    
    plt.imshow(overlay)
    plt.title(f'Наложение пор (красное) и исключений (синеватое): {porosity:.2f}%', pad=5)
    plt.axis('off')

    plt.subplots_adjust(**fig_params['subplot_adjust'])
    plt.tight_layout(**fig_params['tight_layout'])
    plt.savefig(os.path.join(save_directory, 'figure5_overlay.png'), dpi=300, bbox_inches='tight')
    plt.close() 