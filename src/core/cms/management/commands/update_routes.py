import os
import json
from django.core.management.base import BaseCommand, CommandError
from src.core.cms.models import CMSPage


class Command(BaseCommand):
    help = 'Обновляет роуты в базе данных на основе JSON конфигураций'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без фактического обновления БД',
        )
        parser.add_argument(
            '--verbose',
            action='store_true', 
            help='Показать детальную информацию о процессе',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Начинаю обновление роутов...')
        )

        try:
            # Извлекаем пути из конфигураций
            paths_from_config = self.extract_paths_from_configs()
            
            if self.verbose:
                self.stdout.write(f"📋 Найдено {len(paths_from_config)} путей в конфигурациях")
            
            # Получаем текущие пути из БД
            existing_paths = set(CMSPage.objects.values_list('path', flat=True))
            
            if self.verbose:
                self.stdout.write(f"🗄️  Найдено {len(existing_paths)} путей в БД")
            
            # Определяем изменения
            paths_to_add = paths_from_config - existing_paths
            paths_to_remove = existing_paths - paths_from_config
            
            # Показываем статистику
            self.show_statistics(paths_to_add, paths_to_remove, paths_from_config & existing_paths)
            
            if not self.dry_run:
                # Применяем изменения
                self.apply_changes(paths_to_add, paths_to_remove)
                self.stdout.write(
                    self.style.SUCCESS('✅ Обновление роутов завершено успешно!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('🔍 Это был пробный запуск. Изменения не применены.')
                )
                
        except Exception as e:
            raise CommandError(f'❌ Ошибка при обновлении роутов: {str(e)}')

    def extract_paths_from_configs(self):
        """Извлекает все пути из JSON конфигураций"""
        paths = set()
        base_path = self.get_config_base_path()
        
        # Обрабатываем core-routes-config.json
        core_paths = self.extract_from_core_config(base_path)
        paths.update(core_paths)
        
        # Обрабатываем menu-config.json  
        menu_paths = self.extract_from_menu_config(base_path)
        paths.update(menu_paths)
        
        return paths

    def get_config_base_path(self):
        """Получает базовый путь к конфигурациям"""
        return (os.getcwd().replace('\\', '/')).replace('/api', '/client/src/config')

    def extract_from_core_config(self, base_path):
        """Извлекает пути из core-routes-config.json"""
        paths = set()
        core_routes_path = os.path.join(base_path, 'core-routes-config.json')
        
        try:
            with open(core_routes_path, 'r', encoding='utf-8') as file:
                core_config = json.load(file)
                
                # Извлекаем пути из coreRoutes
                if 'coreRoutes' in core_config:
                    for route in core_config['coreRoutes']:
                        if 'path' in route and route['path'] != '/:pathMatch(.*)*':
                            paths.add(route['path'])
                
                # Извлекаем пути из authRoutes
                if 'authRoutes' in core_config:
                    for route in core_config['authRoutes']:
                        if 'path' in route:
                            paths.add(route['path'])
                            
            if self.verbose:
                self.stdout.write(f"📄 Из core-routes-config.json извлечено {len(paths)} путей")
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Ошибка при чтении core-routes-config.json: {e}')
            )
            
        return paths

    def extract_from_menu_config(self, base_path):
        """Извлекает пути из menu-config.json"""
        paths = set()
        menu_config_path = os.path.join(base_path, 'menu-config.json')
        
        try:
            with open(menu_config_path, 'r', encoding='utf-8') as file:
                menu_config = json.load(file)
                
                if 'menuSections' in menu_config:
                    for section in menu_config['menuSections']:
                        # Добавляем основной путь секции
                        if 'route' in section and 'path' in section['route']:
                            main_path = section['route']['path']
                            paths.add(main_path)
                            
                            # Добавляем пути подразделов
                            if 'list' in section and section['list']:
                                for item in section['list']:
                                    # Пропускаем BI offcanvas элементы без path
                                    if 'isOffcanvas' in item and item['isOffcanvas']:
                                        continue
                                        
                                    if 'route' in item and 'path' in item['route']:
                                        sub_path = item['route']['path']
                                        if sub_path.startswith('/'):
                                            paths.add(sub_path)
                                        else:
                                            full_path = f"{main_path.rstrip('/')}/{sub_path}"
                                            paths.add(full_path)
                                            
            if self.verbose:
                self.stdout.write(f"🍽️  Из menu-config.json извлечено {len(paths)} путей")
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Ошибка при чтении menu-config.json: {e}')
            )
            
        return paths

    def show_statistics(self, paths_to_add, paths_to_remove, unchanged_paths):
        """Показывает статистику изменений"""
        self.stdout.write("\n📊 Статистика изменений:")
        self.stdout.write(f"  ➕ Новых путей: {len(paths_to_add)}")
        self.stdout.write(f"  ➖ Путей к удалению: {len(paths_to_remove)}")  
        self.stdout.write(f"  ✅ Без изменений: {len(unchanged_paths)}")
        
        if self.verbose and paths_to_add:
            self.stdout.write("\n➕ Новые пути:")
            for path in sorted(paths_to_add):
                self.stdout.write(f"   + {path}")
                
        if self.verbose and paths_to_remove:
            self.stdout.write("\n➖ Пути к удалению:")
            for path in sorted(paths_to_remove):
                self.stdout.write(f"   - {path}")

    def apply_changes(self, paths_to_add, paths_to_remove):
        """Применяет изменения к базе данных"""
        
        # Добавляем новые пути
        if paths_to_add:
            new_pages = [CMSPage(path=path) for path in paths_to_add]
            CMSPage.objects.bulk_create(new_pages)
            self.stdout.write(
                self.style.SUCCESS(f"➕ Добавлено {len(paths_to_add)} новых путей")
            )
        
        # Удаляем старые пути
        if paths_to_remove:
            deleted_count, _ = CMSPage.objects.filter(path__in=paths_to_remove).delete()
            self.stdout.write(
                self.style.SUCCESS(f"➖ Удалено {deleted_count} устаревших путей")
            ) 