from celery import shared_task
from src.modules.vacancies_parser.headhunter.scripts import parse_vacancies_by_text, parse_all_vacancies, HeadHunterParser
from src.modules.vacancies_parser.headhunter.models import Vacancy

@shared_task
def parse_hh_vacancies_task(
    text_list=None,
    area=113,
    pages=2,
    delay=1.0,
    get_details=True,
    universal=False,
    pages_per_area=5,
    max_total_pages=100,
    areas_only=False,
    config=None
):
    """
    Celery-задача для парсинга вакансий с HeadHunter.
    Возвращает статистику по результатам парсинга.
    """
    import logging
    
    # Получаем логгер для модуля
    logger = logging.getLogger('celery.module.headhunter')
    
    logger.info(f"Запуск задачи parse_hh_vacancies_task с параметрами: text_list={text_list}, universal={universal}")
    
    result = None
    if universal:
        logger.info("Выполняется универсальный парсинг")
        result = parse_all_vacancies(
            pages_per_area=pages_per_area,
            delay=delay,
            max_total_pages=max_total_pages,
            areas_only=areas_only
        )
        logger.info(f"Универсальный парсинг завершен: {result}")
        return {
            'mode': 'universal',
            'areas_processed': result.get('areas_processed'),
            'roles_processed': result.get('roles_processed'),
            'pages_processed': result.get('pages_processed'),
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
    elif text_list:
        logger.info(f"Выполняется парсинг по тексту: {text_list}")
        result = parse_vacancies_by_text(
            text_list=text_list,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        logger.info(f"Парсинг по тексту завершен: {result}")
        return {
            'mode': 'by_text',
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
    else:
        error_msg = 'Необходимо указать text_list или universal=True'
        logger.error(error_msg)
        print(f"ОШИБКА: {error_msg}")  # Дополнительный вывод в консоль
        return {'error': error_msg}

@shared_task
def parse_single_vacancy_task(vacancy_id, force_update=False):
    """
    Celery-задача для парсинга одной вакансии по ID.
    Возвращает результат сохранения/обновления.
    """
    import logging
    
    # Получаем логгер для модуля
    logger = logging.getLogger('celery.module.headhunter')
    
    logger.info(f"Запуск задачи parse_single_vacancy_task для вакансии {vacancy_id}, force_update={force_update}")
    
    parser = HeadHunterParser()
    existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
    if existing_vacancy and not force_update:
        msg = f'Вакансия {vacancy_id} уже есть в базе'
        logger.info(msg)
        return {'status': 'exists', 'message': msg}
    
    vacancy_data = parser.get_vacancy_details(vacancy_id)
    if not vacancy_data or not isinstance(vacancy_data, dict) or 'id' not in vacancy_data:
        msg = f'Вакансия {vacancy_id} не найдена или данные некорректны'
        logger.error(msg)
        return {'status': 'error', 'message': msg}
    
    vacancy = parser.parse_vacancy(vacancy_data)
    if not vacancy:
        msg = 'Ошибка при парсинге вакансии'
        logger.error(msg)
        return {'status': 'error', 'message': msg}
    if existing_vacancy:
        if force_update:
            new_data = {
                'title': vacancy.title,
                'company_name': vacancy.company_name,
                'salary_from': vacancy.salary_from,
                'salary_to': vacancy.salary_to,
                'salary_currency': vacancy.salary_currency,
                'salary_gross': vacancy.salary_gross,
                'city': vacancy.city,
                'address': vacancy.address,
                'description': vacancy.description,
                'requirements': vacancy.requirements,
                'responsibilities': vacancy.responsibilities,
                'employment_type': vacancy.employment_type,
                'experience_level': vacancy.experience_level,
                'key_skills': vacancy.key_skills,
                'schedule_type': vacancy.schedule_type,
                'professional_role': vacancy.professional_role,
                'employer_name': vacancy.employer_name,
                'premium': vacancy.premium,
                'has_test': vacancy.has_test,
                'response_letter_required': vacancy.response_letter_required,
            }
            if existing_vacancy.has_changes(new_data):
                existing_vacancy.create_version(new_data)
                for field, value in new_data.items():
                    setattr(existing_vacancy, field, value)
                existing_vacancy.save()
                return {'status': 'updated', 'message': f'Вакансия {vacancy_id} обновлена'}
            else:
                return {'status': 'no_changes', 'message': 'Изменений не обнаружено'}
        else:
            return {'status': 'exists', 'message': f'Вакансия {vacancy_id} уже есть в базе'}
    else:
        vacancy.save()
        return {'status': 'created', 'message': f'Вакансия {vacancy_id} успешно сохранена'} 