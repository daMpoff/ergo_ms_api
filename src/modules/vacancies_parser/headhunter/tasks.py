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
    result = None
    if universal:
        result = parse_all_vacancies(
            pages_per_area=pages_per_area,
            delay=delay,
            max_total_pages=max_total_pages,
            areas_only=areas_only
        )
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
        result = parse_vacancies_by_text(
            text_list=text_list,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        return {
            'mode': 'by_text',
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
    else:
        return {'error': 'Необходимо указать text_list или universal=True'}

@shared_task
def parse_single_vacancy_task(vacancy_id, force_update=False):
    """
    Celery-задача для парсинга одной вакансии по ID.
    Возвращает результат сохранения/обновления.
    """
    parser = HeadHunterParser()
    existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
    if existing_vacancy and not force_update:
        return {'status': 'exists', 'message': f'Вакансия {vacancy_id} уже есть в базе'}
    vacancy_data = parser.get_vacancy_details(vacancy_id)
    if not vacancy_data or not isinstance(vacancy_data, dict) or 'id' not in vacancy_data:
        return {'status': 'error', 'message': f'Вакансия {vacancy_id} не найдена или данные некорректны'}
    vacancy = parser.parse_vacancy(vacancy_data)
    if not vacancy:
        return {'status': 'error', 'message': 'Ошибка при парсинге вакансии'}
    if existing_vacancy:
        if force_update:
            new_data = {
                'title': vacancy.title,
                'company_name': vacancy.company_name,
                'salary_from': vacancy.salary_from,
                'salary_to': vacancy.salary_to,
                'salary_currency': vacancy.salary_currency,
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