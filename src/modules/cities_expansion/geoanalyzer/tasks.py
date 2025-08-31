import gc
import os
import pickle
import traceback

from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings
from django.core.files import File

from src.modules.cities_expansion.geoanalyzer.methods import analyze_city, crop_maps, get_city, make_final_map, open_image
from src.modules.cities_expansion.models import Task, TaskResult
from src.modules.cities_expansion.geoanalyzer.models import GroupCoords
from src.modules.cities_expansion.geoanalyzer.cities import City

logger = get_task_logger(__name__)

@shared_task() 
def process_map_group(task_id: int, files_dict: dict[str, str], coords_id: int, k: int = 2):
    try:
        task = Task.objects.get(task_id=task_id)
        coords = GroupCoords.objects.get(id=coords_id)
        
        print(files_dict)

        # Восстанавливаем файлы из путей
        files: dict[str, File] = {}
        for filename, file_path in files_dict.items():
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    files[filename] = File(f)  # Теперь это снова файловый объект
            else:
                raise FileNotFoundError(f"Файл {file_path} не найден")

        city_map = None
        buildings_map = None
        railways_map = None

        city_map_cropped = None
        buildings_map_cropped = None
        railways_map_cropped = None

        final_map = None
        city_file_pickle = None

        has_generated_masks = False
        has_generated_for_k = False

        for f in files:
            if f.startswith('city_map_image_cropped'):
                city_map_cropped = files[f]
            elif f.startswith('buildings_map_image_cropped'):
                buildings_map_cropped = files[f]
            elif f.startswith('railways_map_image_cropped'):
                railways_map_cropped = files[f]
            elif f.startswith('city_map'):
                city_map = files[f]
            elif f.startswith('buildings_map'):
                buildings_map = files[f]
            elif f.startswith('railways_map'):
                railways_map = files[f]
            elif f.startswith('final_map'):
                final_map = files[f]
            elif f == 'city.pickle':
                city_file_pickle = files[f]
            elif f.startswith(f'urban_coverage_ratio_plot_{k}'):
                has_generated_for_k = True
            elif f.startswith(f'building_mask'):
                has_generated_masks = True
        
        task.status_description = 'Карты обрезаются'
        task.save()

        if city_map_cropped is None or buildings_map_cropped is None:
            maps = crop_maps(coords.group, city_map, buildings_map, railways_map)
            city_map_cropped = maps[0]
            
            buildings_map_cropped = maps[1]
            if len(maps) > 2:
                railways_map_cropped = maps[2]
        else:
            city_map_cropped = open_image(city_map_cropped)
            buildings_map_cropped = open_image(buildings_map_cropped)

            if railways_map_cropped is not None:
                railways_map_cropped = open_image(railways_map_cropped)


        del city_map
        del buildings_map
        del railways_map
        gc.collect()

        task.status_description = 'Делается итоговая карта с цветовым кодированием'
        task.save()

        if final_map is None:
            final_map = make_final_map(coords.group, city_map_cropped, buildings_map_cropped, railways_map_cropped)
        else:
            final_map = open_image(final_map)


        del city_map_cropped
        del buildings_map_cropped
        del railways_map_cropped
        gc.collect()

        if final_map.height > 6500 or final_map.width > 6500:
            # Высчитываем коэффициент масштабирования
            scaling_factor = min(6500 / final_map.width, 6500 / final_map.height)
            
            # Высчитываем новые размеры сторон
            new_width = int(final_map.width * scaling_factor)
            new_height = int(final_map.height * scaling_factor)
            
            # Масштабируем изображение
            final_map = final_map.resize((new_width, new_height))

        task.status_description = 'Переходим к созданию объектной карты города'
        task.save()

        city: City = None

        if city_file_pickle is None:
            city = get_city(final_map, coords, task)
        else:
            with city_file_pickle.open('rb') as file:
                city = pickle.load(file)
        
        task.status_description = 'Объектная карта города создана. Анализируем...'
        task.save()

        del final_map
        gc.collect()

        if not has_generated_for_k:
            analyze_results = analyze_city(city, coords.group, k, has_generated_masks)
        

            task.status = Task.StatusChoices.FINISHED
            task.status_description = "Карта успешно проанализирована."
            task.save()

            task_results = TaskResult()
            task_results.task = task
            task_results.result = analyze_results
            task_results.save()
        else:
            task.status = Task.StatusChoices.FAILED
            task.status_description = "Карта уже была проанализирована на таком количестве кластеров."
            task.save()

    except Exception as e:
        error_traceback = traceback.format_exc()
        task = Task.objects.get(task_id=task_id)
        task.status = Task.StatusChoices.FAILED
        task.status_description = f'{str(e)}\n\nTraceback:\n{error_traceback}'
        task.save()

        logger.error(f"Task {task_id} failed: {str(e)}\n{error_traceback}")