from src.core.cms.models import CMSPage

import os
import json

def create_default_data(apps, schema_editor):
    PermissionMark = apps.get_model('cms', 'PermissionMark')

    permission_marks = [
        {'name': 'ComponentAccessionToRead', 'id': 1},
        {'name': 'ComponentAccessionToReadAndWrite', 'id': 2},
        {'name': 'PageAccession', 'id': 3},
        {'name': 'AdminAccession', 'id': 4},
    ]    

    for mark_data in permission_marks:
        PermissionMark.objects.get_or_create(
            id=mark_data['id'],
            defaults={'name': mark_data['name']}
        )

    paths = []
    base_path = (os.getcwd().replace('\\','/')).replace('/api','/client/src/config')
    
    # Обрабатываем core-routes-config.json
    core_routes_path = os.path.join(base_path, 'core-routes-config.json')
    try:
        with open(core_routes_path, 'r', encoding='utf-8') as file:
            core_config = json.load(file)
            
            # Извлекаем пути из coreRoutes
            if 'coreRoutes' in core_config:
                for route in core_config['coreRoutes']:
                    if 'path' in route and route['path'] != '/:pathMatch(.*)*':
                        paths.append(route['path'])
            
            # Извлекаем пути из authRoutes
            if 'authRoutes' in core_config:
                for route in core_config['authRoutes']:
                    if 'path' in route:
                        paths.append(route['path'])
                        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка при чтении core-routes-config.json: {e}")

    # Обрабатываем menu-config.json
    menu_config_path = os.path.join(base_path, 'menu-config.json')
    try:
        with open(menu_config_path, 'r', encoding='utf-8') as file:
            menu_config = json.load(file)
            
            if 'menuSections' in menu_config:
                for section in menu_config['menuSections']:
                    # Добавляем основной путь секции
                    if 'route' in section and 'path' in section['route']:
                        main_path = section['route']['path']
                        paths.append(main_path)
                        
                        # Добавляем пути подразделов
                        if 'list' in section and section['list']:
                            for item in section['list']:
                                if 'route' in item and 'path' in item['route']:
                                    # Формируем полный путь: основной_путь + подпуть
                                    sub_path = item['route']['path']
                                    if sub_path.startswith('/'):
                                        # Если подпуть начинается с /, используем его как есть
                                        paths.append(sub_path)
                                    else:
                                        # Иначе комбинируем с основным путем
                                        full_path = f"{main_path.rstrip('/')}/{sub_path}"
                                        paths.append(full_path)
                                        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка при чтении menu-config.json: {e}")

    # Удаляем дубликаты и создаем записи в БД
    unique_paths = list(set(paths))
    for path in unique_paths:
        if path:  # Проверяем что путь не пустой
            CMSPage.objects.get_or_create(path=path)