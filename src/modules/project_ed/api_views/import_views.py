import re
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from ..models import Category, Subcategory, EventBlock, Event
# Удаляем импорт жестких сопоставлений - теперь используем гибкий поиск


def extract_years(date_string):
    """Извлечь годы из строки типа '2023-2025 гг.'"""
    if not date_string or pd.isna(date_string):
        return None, None
    
    date_string = str(date_string).strip()
    
    # Паттерн для диапазона годов
    pattern = r'(\d{4})-(\d{4})\s*гг?\.?'
    match = re.search(pattern, date_string)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Попробовать одиночный год
    single_year = re.search(r'(\d{4})\s*г\.?', date_string)
    if single_year:
        year = int(single_year.group(1))
        return year, year
    
    return None, None


def extract_letter_code(block_code):
    """Извлечь буквенный код из кода блока мероприятий (например, ПК1 -> ПК)"""
    if not block_code or pd.isna(block_code):
        return None
    
    block_code = str(block_code).strip()
    
    # Паттерн для извлечения буквенной части (все символы до первой цифры)
    pattern = r'^([А-Яа-яA-Za-z]+)'
    match = re.match(pattern, block_code)
    
    if match:
        letter_code = match.group(1).upper()
        return letter_code
    
    return None


def check_event_block_exists(block_code, block_title):
    """Проверить, существует ли блок мероприятий с таким кодом или названием"""
    if not block_code and not block_title:
        return None
    
    # Ищем по коду
    if block_code:
        existing_block = EventBlock.objects.filter(code=block_code).first()
        if existing_block:
            return existing_block
    
    # Ищем по названию (точное совпадение)
    if block_title:
        existing_block = EventBlock.objects.filter(title__iexact=block_title).first()
        if existing_block:
            return existing_block
    
    return None


def check_event_exists(event_code, event_name, event_block=None):
    """Проверить, существует ли мероприятие с таким кодом или названием"""
    if not event_code and not event_name:
        return None
    
    # Фильтруем по блоку, если указан
    events_query = Event.objects.all()
    if event_block:
        events_query = events_query.filter(block=event_block)
    
    # Ищем по коду
    if event_code:
        existing_event = events_query.filter(code=event_code).first()
        if existing_event:
            return existing_event
    
    # Ищем по названию (точное совпадение)
    if event_name:
        existing_event = events_query.filter(name__iexact=event_name).first()
        if existing_event:
            return existing_event
    
    return None




def find_subcategory_by_letter_code(letter_code):
    """Найти подкатегорию по буквенному коду - улучшенный поиск"""
    if not letter_code:
        return None
    
    # Специальная обработка для кодов стратегических проектов (П1, П2, П3, П4, П5)
    if letter_code in ['П1', 'П2', 'П3', 'П4', 'П5']:
        project_number = letter_code[1]  # Извлекаем номер
        # Ищем подкатегорию с номером проекта (разные варианты написания)
        subcategory = Subcategory.objects.filter(
            name__icontains=f'проект №{project_number}',
            category__name__icontains='категория б'
        ).select_related('category').first()
        
        if not subcategory:
            # Пробуем альтернативные варианты поиска
            subcategory = Subcategory.objects.filter(
                name__icontains=f'проект {project_number}',
                category__name__icontains='категория б'
            ).select_related('category').first()
        
        if subcategory:
            return subcategory
    
    # 1. Поиск по точному совпадению кода в названии подкатегории
    subcategory = Subcategory.objects.filter(
        name__icontains=letter_code
    ).select_related('category').first()
    
    if subcategory:
        return subcategory
    
    # 2. Поиск по частичному совпадению кода в названии подкатегории
    subcategories = Subcategory.objects.filter(
        name__icontains=letter_code
    ).select_related('category')
    
    if subcategories.exists():
        return subcategories.first()
    
    return None


def find_category_and_subcategory_by_code(block_code, project_name=None):
    """Найти категорию и подкатегорию по коду блока мероприятий"""
    if not block_code or pd.isna(block_code):
        return None, None
    
    
    # Сначала всегда ищем точное совпадение по названию (если есть название)
    if project_name:
        subcategory = Subcategory.objects.filter(
            name__iexact=project_name
        ).select_related('category').first()
        
        if subcategory:
            return subcategory.category, subcategory
        
        # Если точное совпадение не найдено, ищем частичное для стратегических проектов
        if 'стратегический проект' in project_name.lower():
            # Ищем по номеру проекта
            import re
            project_number_match = re.search(r'проект\s*№?(\d+)', project_name.lower())
            if project_number_match:
                project_number = project_number_match.group(1)
                subcategory = Subcategory.objects.filter(
                    name__icontains=f'проект №{project_number}',
                    category__name__icontains='категория б'
                ).select_related('category').first()
                
                if subcategory:
                    return subcategory.category, subcategory
    
    # Если точное совпадение по названию не найдено, ищем по коду
    letter_code = extract_letter_code(block_code)
    
    if letter_code:
        subcategory = find_subcategory_by_letter_code(letter_code)
        
        if subcategory:
            return subcategory.category, subcategory
    
    # Если ничего не найдено, используем общий поиск по названию
    if project_name:
        return find_category_and_subcategory(project_name)
    
    return None, None


def find_category_and_subcategory(project_name):
    """Универсальный поиск категории и подкатегории по названию проекта"""
    if not project_name or pd.isna(project_name):
        return None, None
    
    original_name = str(project_name).strip()
    project_name = original_name.lower()
    
    
    # 1. Попытка точного совпадения подкатегории
    subcategory = Subcategory.objects.filter(
        name__iexact=original_name
    ).first()
    
    if subcategory:
        return subcategory.category, subcategory
    
    # 2. Поиск подкатегории по частичному совпадению
    subcategory = Subcategory.objects.filter(
        name__icontains=original_name
    ).first()
    
    if subcategory:
        return subcategory.category, subcategory
    
    # 3. Поиск по ключевым словам в названии подкатегории
    subcategory = find_subcategory_by_keywords(project_name)
    
    if subcategory:
        return subcategory.category, subcategory
    
    # 4. Поиск категории по тематическим ключевым словам
    category = find_category_by_keywords(project_name)
    
    if category:
        return category, None
    
    # 5. Fallback - первая доступная категория
    category = Category.objects.first()
    return category, None


def find_subcategory_by_keywords(project_name):
    """Поиск подкатегории по ключевым словам - улучшенный поиск"""
    if not project_name:
        return None
    
    project_name_lower = project_name.lower()
    
    # Получаем все подкатегории для поиска
    subcategories = Subcategory.objects.all()
    
    # 1. Поиск по точному совпадению названия
    subcategory = subcategories.filter(
        name__iexact=project_name
    ).first()
    
    if subcategory:
        return subcategory
    
    # 2. Поиск по частичному совпадению названия
    subcategory = subcategories.filter(
        name__icontains=project_name
    ).first()
    
    if subcategory:
        return subcategory
    
    # 3. Специальная логика для стратегических проектов
    if 'стратегический проект' in project_name_lower:
        # Ищем по номеру проекта
        import re
        project_number_match = re.search(r'проект\s*№?(\d+)', project_name_lower)
        if project_number_match:
            project_number = project_number_match.group(1)
            # Ищем подкатегорию с этим номером проекта
            subcategory = subcategories.filter(
                name__icontains=f'проект №{project_number}'
            ).first()
            if subcategory:
                return subcategory
    
    # 4. Поиск по ключевым словам - разбиваем название проекта на слова
    project_words = [word.strip() for word in project_name_lower.split() if len(word.strip()) >= 3]
    
    if not project_words:
        return None
    
    best_match = None
    best_score = 0
    
    for subcategory in subcategories:
        subcategory_name_lower = subcategory.name.lower()
        subcategory_words = [word.strip() for word in subcategory_name_lower.split() if len(word.strip()) >= 3]
        
        # Подсчитываем совпадения слов
        matches = sum(1 for word in project_words if word in subcategory_words)
        
        # Дополнительная проверка: если есть совпадения, проверяем контекст
        if matches > 0:
            # Если это стратегический проект, приоритет у подкатегорий категории Б
            if 'стратегический' in project_name_lower and 'категория б' in subcategory.category.name.lower():
                matches += 10  # Бонус за правильную категорию
            
            # Если это не стратегический проект, но есть слово "цифровой", 
            # проверяем, что это действительно про цифровую трансформацию
            if 'цифровой' in project_name_lower and 'цифровая зрелость' in subcategory_name_lower:
                # Проверяем, что это не просто случайное совпадение
                if 'инфраструктура' in project_name_lower or 'спорт' in project_name_lower:
                    matches = 0  # Исключаем неправильное сопоставление
        
        if matches > 0 and matches > best_score:
            best_match = subcategory
            best_score = matches
    
    return best_match


def find_category_by_keywords(project_name):
    """Поиск категории по тематическим ключевым словам - гибкий поиск"""
    if not project_name:
        return None
    
    project_name_lower = project_name.lower()
    
    # Получаем все категории
    categories = Category.objects.all()
    
    # 1. Поиск по точному совпадению названия
    category = categories.filter(
        name__iexact=project_name
    ).first()
    
    if category:
        return category
    
    # 2. Поиск по частичному совпадению названия
    category = categories.filter(
        name__icontains=project_name
    ).first()
    
    if category:
        return category
    
    # 3. Поиск по ключевым словам - разбиваем название проекта на слова
    project_words = [word.strip() for word in project_name_lower.split() if len(word.strip()) >= 3]
    
    if not project_words:
        return None
    
    best_match = None
    best_score = 0
    
    for category in categories:
        category_name_lower = category.name.lower()
        category_words = [word.strip() for word in category_name_lower.split() if len(word.strip()) >= 3]
        
        # Подсчитываем совпадения слов
        matches = sum(1 for word in project_words if word in category_words)
        
        if matches > 0 and matches > best_score:
            best_match = category
            best_score = matches
    
    return best_match


def parse_excel_file(file):
    """Парсинг Excel файла с мероприятиями"""
    try:
        # Читаем Excel файл
        df = pd.read_excel(file, header=0)
        
        # Проверяем наличие необходимых колонок
        required_columns = ['№ п/п', 'Наименование мероприятия', 'Основные результаты', 'Сроки реализации']
        if not all(col in df.columns for col in required_columns):
            return {
                'success': False,
                'error': f'Отсутствуют необходимые колонки. Ожидаемые: {required_columns}'
            }
        
        results = {
            'blocks_created': 0,
            'events_created': 0,
            'blocks_skipped': 0,  # Пропущенные блоки (дубликаты)
            'events_skipped': 0,  # Пропущенные мероприятия (дубликаты)
            'errors': [],
            'warnings': [],
            'logs': []  # Добавляем детальные логи
        }
        
        current_subcategory_name = None
        current_event_block = None
        order_counter = 1
        total_rows = len(df)
        
        # Начало импорта
        results['logs'].append({
            'level': 'info',
            'message': f'Начало парсинга Excel файла. Всего строк для обработки: {total_rows}'
        })
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Пропускаем пустые строки
                    if pd.isna(row['Наименование мероприятия']):
                        results['logs'].append({
                            'level': 'debug',
                            'message': f'Строка {index + 1}: пропущена (пустое название мероприятия)'
                        })
                        continue
                    
                    name = str(row['Наименование мероприятия']).strip()
                    serial_num = row['№ п/п'] if not pd.isna(row['№ п/п']) else None
                    results_text = str(row['Основные результаты']).strip() if not pd.isna(row['Основные результаты']) else ''
                    dates = str(row['Сроки реализации']).strip() if not pd.isna(row['Сроки реализации']) else ''
                    
                    progress_percent = int(((index + 1) / total_rows) * 100)
                    results['logs'].append({
                        'level': 'info',
                        'message': f'Обработка строки {index + 1}/{total_rows} ({progress_percent}%): "{name}"'
                    })
                    
                    # Определяем тип строки
                    if serial_num is None or pd.isna(serial_num):
                        # Строка с названием подкатегории (объединенные 4 столбца)
                        current_subcategory_name = name
                        results['logs'].append({
                            'level': 'info',
                            'message': f'📂 Найдена подкатегория: "{current_subcategory_name}"'
                        })
                        
                    elif '.' not in str(serial_num):
                        # Строка с блоком мероприятий (код без дроби)
                        block_code = str(serial_num).strip()
                        results['logs'].append({
                            'level': 'info',
                            'message': f'🔧 Обработка блока мероприятий с кодом "{block_code}": "{name}"'
                        })
                        
                        # Проверяем, существует ли уже такой блок мероприятий
                        existing_block = check_event_block_exists(block_code, name)
                        if existing_block:
                            warning_msg = f'⚠️ Блок мероприятий уже существует: код="{existing_block.code}", название="{existing_block.title}" (строка {index + 1})'
                            results['warnings'].append(warning_msg)
                            results['blocks_skipped'] += 1
                            results['logs'].append({
                                'level': 'warn',
                                'message': warning_msg
                            })
                            
                            # Используем существующий блок
                            current_event_block = existing_block
                            results['logs'].append({
                                'level': 'info',
                                'message': f'🔄 Используем существующий блок мероприятий ID={existing_block.id}'
                            })
                            continue
                        
                        # Найти подкатегорию по коду блока
                        results['logs'].append({
                            'level': 'debug',
                            'message': f'🔍 Поиск подкатегории для блока "{block_code}"'
                        })
                        
                        _category, subcategory = find_category_and_subcategory_by_code(block_code, name)
                        
                        if not subcategory:
                            warning_msg = f'⚠️ Не найдена подкатегория для блока "{block_code}": "{name}"'
                            results['warnings'].append(warning_msg)
                            results['logs'].append({
                                'level': 'warn',
                                'message': warning_msg
                            })
                            
                            # Используем первую доступную подкатегорию
                            subcategory = Subcategory.objects.first()
                            fallback_msg = f'🔄 Используем fallback: подкатегория="{subcategory.name if subcategory else None}"'
                            results['logs'].append({
                                'level': 'warn',
                                'message': fallback_msg
                            })
                        else:
                            results['logs'].append({
                                'level': 'success',
                                'message': f'✅ Найдена подкатегория "{subcategory.name}" для блока "{block_code}"'
                            })
                        
                        # Создаем EventBlock
                        current_event_block = EventBlock.objects.create(
                            code=block_code,
                            title=name,
                            description=name,  # Используем название как описание
                            subcategory=subcategory,
                            order=order_counter,
                            is_active=True
                        )
                        
                        results['blocks_created'] += 1
                        order_counter += 1
                        
                        success_msg = f'🎯 Создан блок мероприятий "{block_code}" - "{name}" (всего блоков: {results["blocks_created"]})'
                        results['logs'].append({
                            'level': 'success',
                            'message': success_msg
                        })
                        
                        # Детальная информация о блоке
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   📋 Код: {block_code}'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   📝 Название: {name}'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   🏷️ Подкатегория: {subcategory.name if subcategory else "Не указана"}'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   🔢 Порядок: {order_counter - 1}'
                        })
                        
                    else:
                        # Строка с мероприятием (дробный код)
                        if not current_event_block:
                            error_msg = f'❌ Строка {index + 1}: мероприятие "{serial_num}" без блока мероприятий'
                            results['errors'].append(error_msg)
                            results['logs'].append({
                                'level': 'error',
                                'message': error_msg
                            })
                            continue
                        
                        event_code = str(serial_num).strip()
                        results['logs'].append({
                            'level': 'info',
                            'message': f'📋 Обработка мероприятия с кодом "{event_code}": "{name}"'
                        })
                        
                        # Проверяем, существует ли уже такое мероприятие
                        existing_event = check_event_exists(event_code, name, current_event_block)
                        if existing_event:
                            warning_msg = f'⚠️ Мероприятие уже существует: код="{existing_event.code}", название="{existing_event.name}" (строка {index + 1})'
                            results['warnings'].append(warning_msg)
                            results['events_skipped'] += 1
                            results['logs'].append({
                                'level': 'warn',
                                'message': warning_msg
                            })
                            
                            results['logs'].append({
                                'level': 'info',
                                'message': f'🔄 Пропускаем дубликат мероприятия ID={existing_event.id}'
                            })
                            continue
                        
                        # Извлекаем годы
                        start_year, end_year = extract_years(dates)
                        if start_year and end_year:
                            results['logs'].append({
                                'level': 'info',
                                'message': f'📅 Период реализации: {start_year}-{end_year} гг.'
                            })
                        elif start_year:
                            results['logs'].append({
                                'level': 'info',
                                'message': f'📅 Год реализации: {start_year} г.'
                            })
                        else:
                            results['logs'].append({
                                'level': 'warn',
                                'message': f'⚠️ Не удалось определить период реализации из строки: "{dates}"'
                            })
                        
                        # Создаем Event
                        event = Event.objects.create(
                            block=current_event_block,
                            code=event_code,
                            name=name,
                            results=results_text,
                            start_year=start_year,
                            end_year=end_year,
                            order=order_counter,
                            is_active=True
                        )
                        
                        results['events_created'] += 1
                        order_counter += 1
                        
                        success_msg = f'✅ Создано мероприятие "{event_code}" - "{name}" (всего мероприятий: {results["events_created"]})'
                        results['logs'].append({
                            'level': 'success',
                            'message': success_msg
                        })
                        
                        # Детальная информация о мероприятии
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   📋 Код: {event_code}'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   📝 Название: {name}'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   🏢 Блок: {current_event_block.code} - {current_event_block.title}'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   📅 Период: {start_year}-{end_year} гг.' if start_year and end_year else f'   📅 Год: {start_year} г.' if start_year else '   📅 Период не указан'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   📊 Результаты: {results_text[:100]}{"..." if len(results_text) > 100 else ""}' if results_text else '   📊 Результаты не указаны'
                        })
                        results['logs'].append({
                            'level': 'info',
                            'message': f'   🔢 Порядок: {order_counter - 1}'
                        })
                
                except Exception as e:
                    error_msg = f'❌ Ошибка при обработке строки {index + 1}: {str(e)}'
                    results['errors'].append(error_msg)
                    results['logs'].append({
                        'level': 'error',
                        'message': error_msg
                    })
        
        # Итоговая статистика
        results['success'] = True
        final_msg = f'🎉 Импорт завершен! Создано блоков: {results["blocks_created"]}, мероприятий: {results["events_created"]}, пропущено блоков: {results["blocks_skipped"]}, пропущено мероприятий: {results["events_skipped"]}, ошибок: {len(results["errors"])}, предупреждений: {len(results["warnings"])}'
        results['logs'].append({
            'level': 'success',
            'message': final_msg
        })
        
        return results
        
    except Exception as e:
        error_msg = f'❌ Ошибка при парсинге файла: {str(e)}'
        return {
            'success': False,
            'error': f'Ошибка при чтении файла: {str(e)}',
            'logs': [{'level': 'error', 'message': error_msg}]
        }




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_excel(request):
    """Импорт блоков мероприятий и мероприятий из Excel файла"""
    try:
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Файл не найден'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        # Проверяем тип файла
        if not file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'Поддерживаются только файлы Excel (.xlsx, .xls)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Парсим файл
        result = parse_excel_file(file)
        
        
        if result['success']:
            response_data = {
                'message': 'Импорт завершен успешно',
                'blocksCreated': result['blocks_created'],
                'eventsCreated': result['events_created'],
                'blocksSkipped': result.get('blocks_skipped', 0),
                'eventsSkipped': result.get('events_skipped', 0),
                'errors': result['errors'],
                'warnings': result['warnings'],
                'logs': result.get('logs', [])
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {
                'error': result['error'],
                'blocksCreated': 0,
                'eventsCreated': 0,
                'blocksSkipped': 0,
                'eventsSkipped': 0,
                'errors': result.get('errors', []),
                'warnings': result.get('warnings', []),
                'logs': result.get('logs', [])
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        response_data = {
            'error': f'Внутренняя ошибка сервера: {str(e)}',
            'blocksCreated': 0,
            'eventsCreated': 0,
            'blocksSkipped': 0,
            'eventsSkipped': 0,
            'errors': [f'Внутренняя ошибка сервера: {str(e)}'],
            'warnings': [],
            'logs': [{'level': 'error', 'message': f'❌ Внутренняя ошибка сервера: {str(e)}'}]
        }
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
