from celery import shared_task
from src.modules.vacancies_parser.habr_career.scripts import parse_habr_vacancies, parse_habr_archived_vacancies, parse_habr_all_vacancies


@shared_task(bind=True)
def parse_habr_vacancies_task(self, access_token, pages=5, delay=1.0, get_details=True):
    """
    Celery задача для парсинга вакансий с Хабр Карьеры
    
    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
    """
    try:
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': pages,
                'status': 'Начинаем парсинг вакансий с Хабр Карьеры...'
            }
        )
        
        # Выполняем парсинг
        result = parse_habr_vacancies(
            access_token=access_token,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        
        # Возвращаем результат
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': f'Парсинг завершен. Обработано: {result["total"]}, Новых: {result["new"]}, Обновлено: {result["updated"]}, Ошибок: {result["errors"]}'
        }
        
    except Exception as e:
        # В случае ошибки
        return {
            'status': 'ERROR',
            'error': str(e),
            'message': f'Ошибка при парсинге вакансий: {e}'
        }


@shared_task(bind=True)
def parse_habr_archived_vacancies_task(self, access_token, pages=5, delay=1.0):
    """
    Celery задача для парсинга архивных вакансий с Хабр Карьеры
    
    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
    """
    try:
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': pages,
                'status': 'Начинаем парсинг архивных вакансий с Хабр Карьеры...'
            }
        )
        
        # Выполняем парсинг
        result = parse_habr_archived_vacancies(
            access_token=access_token,
            pages=pages,
            delay=delay
        )
        
        # Возвращаем результат
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': f'Парсинг архивных вакансий завершен. Обработано: {result["total"]}, Новых: {result["new"]}, Обновлено: {result["updated"]}, Ошибок: {result["errors"]}'
        }
        
    except Exception as e:
        # В случае ошибки
        return {
            'status': 'ERROR',
            'error': str(e),
            'message': f'Ошибка при парсинге архивных вакансий: {e}'
        }


@shared_task(bind=True)
def parse_habr_all_vacancies_task(self, access_token, pages=5, delay=1.0, get_details=True):
    """
    Celery задача для парсинга всех вакансий (активных и архивных) с Хабр Карьеры
    
    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
    """
    try:
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': pages * 2,  # Умножаем на 2, так как парсим активные и архивные
                'status': 'Начинаем парсинг всех вакансий с Хабр Карьеры...'
            }
        )
        
        # Парсим все вакансии
        result = parse_habr_all_vacancies(
            access_token=access_token,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        
        total_result = result
        
        # Возвращаем результат
        return {
            'status': 'SUCCESS',
            'result': total_result,
            'message': f'Парсинг всех вакансий завершен. Всего обработано: {total_result["total"]["total"]}, Новых: {total_result["total"]["new"]}, Обновлено: {total_result["total"]["updated"]}, Ошибок: {total_result["total"]["errors"]}'
        }
        
    except Exception as e:
        # В случае ошибки
        return {
            'status': 'ERROR',
            'error': str(e),
            'message': f'Ошибка при парсинге всех вакансий: {e}'
        } 