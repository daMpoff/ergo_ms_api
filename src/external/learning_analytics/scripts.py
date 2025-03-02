import json
import string
import random

def get_technologies(technology_id: int = None):
    """
    Возвращает SQL-запрос и параметры для получения данных о конкретной технологии по её ID.

    Args:
        technology_id (int, optional): ID технологии. Если не указан, возвращает запрос для всех технологий.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и параметры для выполнения запроса.
               - SQL-запрос (str): Запрос для выборки данных о технологии.
               - Параметры (tuple): Кортеж с параметрами для запроса (technology_id).
    """
    return (
        """
        select
            id,
            name,
            description,
            popularity,
            rating
        from
            learning_analytics_technology
        where id = %s
        """,
        (technology_id,),  # Параметр для подстановки в SQL-запрос
    )


def get_all_technologies():
    """
    Возвращает SQL-запрос для получения данных обо всех технологиях.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и пустой кортеж параметров.
               - SQL-запрос (str): Запрос для выборки всех данных из таблицы технологий.
               - Параметры (tuple): Пустой кортеж, так как параметры не требуются.
    """
    return (
        """
        select
            *
        from
            learning_analytics_technology
        """,
        (),  # Пустой кортеж параметров, так как запрос не требует параметров
    )