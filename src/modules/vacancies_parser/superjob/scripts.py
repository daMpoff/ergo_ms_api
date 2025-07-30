import requests
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.utils import timezone
from src.modules.vacancies_parser.superjob.models import SuperJobVacancy

logger = logging.getLogger(__name__)

class SuperJobAPIClient:
    """Клиент для работы с API SuperJob"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://api.superjob.ru/2.0"
        self.headers = {
            'X-Api-App-Id': api_key,
            'Content-Type': 'application/json'
        } if api_key else {}
    
    def search_vacancies(self, 
                        keyword: str = None,
                        town: str = None,
                        experience: str = None,
                        employment: str = None,
                        schedule: str = None,
                        page: int = 0,
                        count: int = 20) -> Dict[str, Any]:
        """
        Поиск вакансий через API SuperJob
        
        Args:
            keyword: Ключевое слово для поиска
            town: Город
            experience: Опыт работы
            employment: Тип занятости
            schedule: График работы
            page: Номер страницы
            count: Количество вакансий на странице
            
        Returns:
            Dict с результатами поиска
        """
        url = f"{self.base_url}/vacancies/"
        
        params = {
            'page': page,
            'count': count
        }
        
        if keyword:
            params['keyword'] = keyword
        if town:
            params['town'] = town
        if experience:
            params['experience'] = experience
        if employment:
            params['employment'] = employment
        if schedule:
            params['schedule'] = schedule
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к SuperJob API: {e}")
            return {"objects": [], "total": 0, "error": str(e)}
    
    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о вакансии
        
        Args:
            vacancy_id: ID вакансии
            
        Returns:
            Dict с детальной информацией о вакансии
        """
        url = f"{self.base_url}/vacancies/{vacancy_id}/"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении деталей вакансии {vacancy_id}: {e}")
            return None


def parse_vacancy_data(vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Парсинг данных вакансии из API SuperJob
    
    Args:
        vacancy_data: Данные вакансии из API
        
    Returns:
        Dict с обработанными данными для сохранения в БД
    """
    # Обработка зарплаты
    salary_from = None
    salary_to = None
    salary_currency = None
    salary_gross = True
    
    if vacancy_data.get('payment_from') and vacancy_data.get('payment_from') > 0:
        salary_from = vacancy_data['payment_from']
    if vacancy_data.get('payment_to') and vacancy_data.get('payment_to') > 0:
        salary_to = vacancy_data['payment_to']
    
    if vacancy_data.get('currency'):
        salary_currency = vacancy_data['currency']
    
    # Обработка типа занятости
    employment_type = None
    if vacancy_data.get('type_of_work'):
        employment_map = {
            'full': 'Полная занятость',
            'part': 'Частичная занятость',
            'project': 'Проектная работа',
            'volunteer': 'Волонтерство',
            'probation': 'Стажировка'
        }
        employment_type = employment_map.get(vacancy_data['type_of_work']['id'], vacancy_data['type_of_work']['title'])
    
    # Обработка опыта
    experience_level = None
    if vacancy_data.get('experience'):
        experience_map = {
            'noExperience': 'Без опыта',
            'between1And3': 'От 1 до 3 лет',
            'between3And6': 'От 3 до 6 лет',
            'moreThan6': 'Более 6 лет'
        }
        experience_level = experience_map.get(vacancy_data['experience']['id'], vacancy_data['experience']['title'])
    
    # Обработка графика работы
    schedule_type = None
    if vacancy_data.get('place_of_work'):
        schedule_map = {
            'fullDay': 'Полный день',
            'shift': 'Сменный график',
            'flexible': 'Гибкий график',
            'remote': 'Удаленная работа',
            'flyInFlyOut': 'Вахтовый метод'
        }
        schedule_type = schedule_map.get(vacancy_data['place_of_work']['id'], vacancy_data['place_of_work']['title'])
    
    # Обработка навыков
    skills = []
    if vacancy_data.get('catalogues'):
        for catalogue in vacancy_data['catalogues']:
            if catalogue.get('positions'):
                for position in catalogue['positions']:
                    if position.get('title'):
                        skills.append(position['title'])
    
    # Обработка ключевых навыков
    key_skills = []
    if vacancy_data.get('key_skills'):
        key_skills = [skill['title'] for skill in vacancy_data['key_skills'] if skill.get('title')]
    
    # Обработка даты публикации
    published_at = timezone.now()
    if vacancy_data.get('date_published'):
        try:
            published_at = datetime.fromtimestamp(vacancy_data['date_published'])
            published_at = timezone.make_aware(published_at)
        except (ValueError, TypeError):
            pass
    
    return {
        'title': vacancy_data.get('profession', ''),
        'company_name': vacancy_data.get('firm_name', ''),
        'salary_from': salary_from,
        'salary_to': salary_to,
        'salary_currency': salary_currency,
        'salary_gross': salary_gross,
        'city': vacancy_data.get('town', {}).get('title', '') if vacancy_data.get('town') else None,
        'address': vacancy_data.get('address', ''),
        'description': vacancy_data.get('candidat', ''),
        'requirements': vacancy_data.get('requirement', ''),
        'responsibilities': vacancy_data.get('responsibility', ''),
        'employment_type': employment_type,
        'experience_level': experience_level,
        'skills': skills,
        'key_skills': key_skills,
        'superjob_id': str(vacancy_data.get('id', '')),
        'url': vacancy_data.get('link', ''),
        'company_url': vacancy_data.get('firm_name', ''),
        'schedule_type': schedule_type,
        'professional_role': vacancy_data.get('catalogues', [{}])[0].get('title', '') if vacancy_data.get('catalogues') else None,
        'employer_id': str(vacancy_data.get('id_client', '')),
        'employer_name': vacancy_data.get('firm_name', ''),
        'employer_trusted': vacancy_data.get('is_archive', False),
        'premium': vacancy_data.get('is_star', False),
        'published_at': published_at
    }


def save_vacancy_to_db(vacancy_data: Dict[str, Any]) -> Optional[SuperJobVacancy]:
    """
    Сохранение вакансии в базу данных
    
    Args:
        vacancy_data: Данные вакансии для сохранения
        
    Returns:
        Объект вакансии или None в случае ошибки
    """
    try:
        superjob_id = vacancy_data.get('superjob_id')
        if not superjob_id:
            logger.warning("Отсутствует superjob_id для вакансии")
            return None
        
        # Проверяем, существует ли уже такая вакансия
        existing_vacancy = SuperJobVacancy.objects.filter(superjob_id=superjob_id).first()
        
        if existing_vacancy:
            # Проверяем, есть ли изменения
            if existing_vacancy.has_changes(vacancy_data):
                # Создаем новую версию
                existing_vacancy.create_version(vacancy_data)
                # Обновляем данные
                for field, value in vacancy_data.items():
                    if hasattr(existing_vacancy, field):
                        setattr(existing_vacancy, field, value)
                existing_vacancy.save()
                logger.info(f"Обновлена вакансия: {existing_vacancy.title}")
            return existing_vacancy
        else:
            # Создаем новую вакансию
            vacancy = SuperJobVacancy.objects.create(**vacancy_data)
            logger.info(f"Создана новая вакансия: {vacancy.title}")
            return vacancy
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении вакансии: {e}")
        return None


def parse_vacancies_by_text(text: str, 
                           town: str = None,
                           experience: str = None,
                           employment: str = None,
                           schedule: str = None,
                           max_pages: int = 5,
                           delay: float = 1.0,
                           api_key: str = None) -> Dict[str, Any]:
    """
    Парсинг вакансий по текстовому запросу
    
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
    client = SuperJobAPIClient(api_key)
    total_vacancies = 0
    saved_vacancies = 0
    updated_vacancies = 0
    errors = 0
    
    logger.info(f"Начинаем парсинг вакансий по запросу: '{text}'")
    
    for page in range(max_pages):
        try:
            # Получаем список вакансий
            search_result = client.search_vacancies(
                keyword=text,
                town=town,
                experience=experience,
                employment=employment,
                schedule=schedule,
                page=page,
                count=20
            )
            
            if not search_result.get('objects'):
                logger.info(f"На странице {page + 1} вакансий не найдено")
                break
            
            vacancies = search_result['objects']
            total_vacancies += len(vacancies)
            
            logger.info(f"Обрабатываем страницу {page + 1}, найдено {len(vacancies)} вакансий")
            
            # Обрабатываем каждую вакансию
            for vacancy_data in vacancies:
                try:
                    # Парсим данные вакансии
                    parsed_data = parse_vacancy_data(vacancy_data)
                    
                    # Сохраняем в базу данных
                    vacancy = save_vacancy_to_db(parsed_data)
                    
                    if vacancy:
                        if vacancy.created_at == vacancy.updated_at:
                            saved_vacancies += 1
                        else:
                            updated_vacancies += 1
                    else:
                        errors += 1
                        
                except Exception as e:
                    logger.error(f"Ошибка при обработке вакансии: {e}")
                    errors += 1
            
            # Задержка между запросами
            if page < max_pages - 1:
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"Ошибка при обработке страницы {page + 1}: {e}")
            errors += 1
    
    result = {
        'total_vacancies': total_vacancies,
        'saved_vacancies': saved_vacancies,
        'updated_vacancies': updated_vacancies,
        'errors': errors,
        'search_query': text
    }
    
    logger.info(f"Парсинг завершен. Результаты: {result}")
    return result


def parse_all_vacancies(max_pages_per_query: int = 3,
                       delay: float = 1.0,
                       api_key: str = None) -> Dict[str, Any]:
    """
    Универсальный парсинг всех вакансий
    
    Args:
        max_pages_per_query: Максимальное количество страниц для каждого запроса
        delay: Задержка между запросами
        api_key: API ключ SuperJob
        
    Returns:
        Dict с общими результатами парсинга
    """
    # Список популярных запросов для парсинга
    search_queries = [
        'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go',
        'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask', 'Laravel',
        'DevOps', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
        'Data Science', 'Machine Learning', 'AI', 'Big Data',
        'Frontend', 'Backend', 'Full Stack', 'Mobile', 'iOS', 'Android',
        'QA', 'Testing', 'Automation', 'Selenium', 'Cypress',
        'Project Manager', 'Product Manager', 'Scrum Master', 'Agile',
        'UI/UX', 'Design', 'Graphic Design', 'Web Design',
        'Marketing', 'SEO', 'SMM', 'Content Marketing',
        'Sales', 'Business Development', 'Account Manager',
        'HR', 'Recruiter', 'Talent Acquisition',
        'Finance', 'Accounting', 'Analyst', 'Auditor',
        'Legal', 'Lawyer', 'Attorney',
        'Medicine', 'Doctor', 'Nurse', 'Therapist',
        'Education', 'Teacher', 'Professor', 'Tutor',
        'Engineering', 'Mechanical', 'Electrical', 'Civil',
        'Construction', 'Architect', 'Designer',
        'Transport', 'Driver', 'Logistics', 'Supply Chain',
        'Retail', 'Sales', 'Cashier', 'Manager',
        'Hospitality', 'Hotel', 'Restaurant', 'Tourism',
        'Media', 'Journalist', 'Editor', 'Writer',
        'Sports', 'Fitness', 'Coach', 'Trainer',
        'Security', 'Guard', 'Protection',
        'Cleaning', 'Maintenance', 'Repair',
        'Agriculture', 'Farming', 'Gardening',
        'Manufacturing', 'Production', 'Assembly',
        'Research', 'Scientist', 'Laboratory',
        'Government', 'Public Service', 'Administration'
    ]
    
    total_results = {
        'total_queries': len(search_queries),
        'total_vacancies': 0,
        'total_saved': 0,
        'total_updated': 0,
        'total_errors': 0,
        'queries_processed': 0,
        'queries_failed': 0
    }
    
    logger.info(f"Начинаем универсальный парсинг {len(search_queries)} запросов")
    
    for i, query in enumerate(search_queries, 1):
        try:
            logger.info(f"Обрабатываем запрос {i}/{len(search_queries)}: '{query}'")
            
            result = parse_vacancies_by_text(
                text=query,
                max_pages=max_pages_per_query,
                delay=delay,
                api_key=api_key
            )
            
            total_results['total_vacancies'] += result['total_vacancies']
            total_results['total_saved'] += result['saved_vacancies']
            total_results['total_updated'] += result['updated_vacancies']
            total_results['total_errors'] += result['errors']
            total_results['queries_processed'] += 1
            
            logger.info(f"Запрос '{query}' обработан. Найдено: {result['total_vacancies']}, "
                       f"Сохранено: {result['saved_vacancies']}, Обновлено: {result['updated_vacancies']}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса '{query}': {e}")
            total_results['queries_failed'] += 1
            total_results['total_errors'] += 1
        
        # Задержка между запросами
        if i < len(search_queries):
            time.sleep(delay * 2)  # Увеличенная задержка между разными запросами
    
    logger.info(f"Универсальный парсинг завершен. Общие результаты: {total_results}")
    return total_results


def get_vacancy_details(vacancy_id: str, api_key: str = None) -> Optional[Dict[str, Any]]:
    """
    Получение детальной информации о конкретной вакансии
    
    Args:
        vacancy_id: ID вакансии
        api_key: API ключ SuperJob
        
    Returns:
        Dict с детальной информацией о вакансии
    """
    client = SuperJobAPIClient(api_key)
    return client.get_vacancy_details(vacancy_id) 