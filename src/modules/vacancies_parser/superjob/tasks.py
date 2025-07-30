import logging
from celery import shared_task
from typing import Dict, Any, Optional
from src.modules.vacancies_parser.superjob.scripts import (
    parse_vacancies_by_text,
    parse_all_vacancies,
    get_vacancy_details
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='parse_superjob_vacancies')
def parse_superjob_vacancies_task(self, 
                                 text: str = None,
                                 town: str = None,
                                 experience: str = None,
                                 employment: str = None,
                                 schedule: str = None,
                                 max_pages: int = 5,
                                 delay: float = 1.0,
                                 api_key: str = None) -> Dict[str, Any]:
    """
    Задача Celery для парсинга вакансий SuperJob по текстовому запросу
    
    Args:
        text: Текст для поиска
        town: Город
        experience: Опыт работы
        employment: Тип занятости
        schedule: График работы
        max_pages: Максимальное количество страниц
        delay: Задержка между запросами
        api_key: API ключ SuperJob
        
    Returns:
        Dict с результатами парсинга
    """
    try:
        logger.info(f"Начинаем задачу парсинга SuperJob вакансий для запроса: '{text}'")
        
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': max_pages,
                'status': f'Начинаем парсинг вакансий по запросу: {text}'
            }
        )
        
        # Выполняем парсинг
        result = parse_vacancies_by_text(
            text=text,
            town=town,
            experience=experience,
            employment=employment,
            schedule=schedule,
            max_pages=max_pages,
            delay=delay,
            api_key=api_key
        )
        
        logger.info(f"Задача парсинга SuperJob завершена успешно. Результаты: {result}")
        
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': f'Парсинг завершен. Найдено: {result["total_vacancies"]}, '
                      f'Сохранено: {result["saved_vacancies"]}, Обновлено: {result["updated_vacancies"]}'
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче парсинга SuperJob вакансий: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при парсинге вакансий: {e}'
        }


@shared_task(bind=True, name='parse_all_superjob_vacancies')
def parse_all_superjob_vacancies_task(self,
                                     max_pages_per_query: int = 3,
                                     delay: float = 1.0,
                                     api_key: str = None) -> Dict[str, Any]:
    """
    Задача Celery для универсального парсинга всех вакансий SuperJob
    
    Args:
        max_pages_per_query: Максимальное количество страниц для каждого запроса
        delay: Задержка между запросами
        api_key: API ключ SuperJob
        
    Returns:
        Dict с общими результатами парсинга
    """
    try:
        logger.info("Начинаем задачу универсального парсинга SuperJob вакансий")
        
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,  # Примерное количество запросов
                'status': 'Начинаем универсальный парсинг вакансий'
            }
        )
        
        # Выполняем универсальный парсинг
        result = parse_all_vacancies(
            max_pages_per_query=max_pages_per_query,
            delay=delay,
            api_key=api_key
        )
        
        logger.info(f"Задача универсального парсинга SuperJob завершена успешно. Результаты: {result}")
        
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': f'Универсальный парсинг завершен. Обработано запросов: {result["queries_processed"]}, '
                      f'Найдено вакансий: {result["total_vacancies"]}, Сохранено: {result["total_saved"]}'
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче универсального парсинга SuperJob вакансий: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при универсальном парсинге вакансий: {e}'
        }


@shared_task(bind=True, name='get_superjob_vacancy_details')
def get_superjob_vacancy_details_task(self,
                                     vacancy_id: str,
                                     api_key: str = None) -> Dict[str, Any]:
    """
    Задача Celery для получения детальной информации о вакансии SuperJob
    
    Args:
        vacancy_id: ID вакансии
        api_key: API ключ SuperJob
        
    Returns:
        Dict с детальной информацией о вакансии
    """
    try:
        logger.info(f"Начинаем задачу получения деталей вакансии SuperJob: {vacancy_id}")
        
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 1,
                'status': f'Получаем детали вакансии: {vacancy_id}'
            }
        )
        
        # Получаем детали вакансии
        result = get_vacancy_details(vacancy_id, api_key)
        
        if result:
            logger.info(f"Детали вакансии SuperJob получены успешно: {vacancy_id}")
            return {
                'status': 'SUCCESS',
                'result': result,
                'message': f'Детали вакансии получены: {result.get("profession", "Неизвестная вакансия")}'
            }
        else:
            logger.warning(f"Не удалось получить детали вакансии SuperJob: {vacancy_id}")
            return {
                'status': 'FAILURE',
                'error': 'Вакансия не найдена или недоступна',
                'message': f'Не удалось получить детали вакансии: {vacancy_id}'
            }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче получения деталей вакансии SuperJob: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при получении деталей вакансии: {e}'
        }


@shared_task(bind=True, name='parse_superjob_vacancies_by_config')
def parse_superjob_vacancies_by_config_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Задача Celery для парсинга вакансий SuperJob по конфигурации
    
    Args:
        config: Конфигурация для парсинга
        
    Returns:
        Dict с результатами парсинга
    """
    try:
        logger.info("Начинаем задачу парсинга SuperJob вакансий по конфигурации")
        
        # Извлекаем параметры из конфигурации
        text = config.get('text')
        town = config.get('town')
        experience = config.get('experience')
        employment = config.get('employment')
        schedule = config.get('schedule')
        max_pages = config.get('max_pages', 5)
        delay = config.get('delay', 1.0)
        api_key = config.get('api_key')
        
        # Обновляем статус задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': max_pages,
                'status': f'Начинаем парсинг вакансий по конфигурации: {text}'
            }
        )
        
        # Выполняем парсинг
        result = parse_vacancies_by_text(
            text=text,
            town=town,
            experience=experience,
            employment=employment,
            schedule=schedule,
            max_pages=max_pages,
            delay=delay,
            api_key=api_key
        )
        
        logger.info(f"Задача парсинга SuperJob по конфигурации завершена успешно. Результаты: {result}")
        
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': f'Парсинг по конфигурации завершен. Найдено: {result["total_vacancies"]}, '
                      f'Сохранено: {result["saved_vacancies"]}, Обновлено: {result["updated_vacancies"]}'
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче парсинга SuperJob вакансий по конфигурации: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при парсинге вакансий по конфигурации: {e}'
        }


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Получение статуса задачи Celery
    
    Args:
        task_id: ID задачи
        
    Returns:
        Dict с информацией о статусе задачи
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    
    if result.ready():
        if result.successful():
            return {
                'status': 'SUCCESS',
                'result': result.result,
                'task_id': task_id
            }
        else:
            return {
                'status': 'FAILURE',
                'error': str(result.result),
                'task_id': task_id
            }
    else:
        return {
            'status': 'PENDING',
            'info': result.info,
            'task_id': task_id
        } 