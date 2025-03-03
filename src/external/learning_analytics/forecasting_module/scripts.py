import json
import string

def get_specialities(speciality_id: int = None):
    """
    Возвращает SQL-запрос и параметры для получения данных о конкретной технологии по её ID.

    Args:
        speciality_id (int, optional): ID специальности. Если не указан, возвращает запрос для всех технологий.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и параметры для выполнения запроса.
               - SQL-запрос (str): Запрос для выборки данных о технологии.
               - Параметры (tuple): Кортеж с параметрами для запроса (speciality_id).
    """
    return (
        """
        select
            id,
            code,
            name,
            specialization,
            department,
            faculty,
            education_duration,
            year_of_admission
        from
            forecasting_module_speciality
        where id = %s
        """,
        (speciality_id,),  # Параметр для подстановки в SQL-запрос
    )

def get_all_specialities():
    """
    Возвращает SQL-запрос для получения данных обо всех специальностях.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и пустой кортеж параметров.
               - SQL-запрос (str): Запрос для выборки всех данных из таблицы специальностей.
               - Параметры (tuple): Пустой кортеж, так как параметры не требуются.
    """
    return (
        """
        select
            *
        from
            forecasting_module_speciality
        """,
        (),  # Пустой кортеж параметров, так как запрос не требует параметров
    )