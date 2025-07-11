import json
import string
import random

def get_employers(employer_id: int = None):
    """
    Возвращает SQL-запрос и параметры для получения данных о работодателях.

    Args:
        employer_id (int, optional): ID работодателя. Если не указан, возвращает запрос для всех существующих работодателей.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и параметры для выполнения запроса.
               - SQL-запрос (str): Запрос для выборки данных о работодателях.
               - Параметры (tuple): Кортеж с параметрами для запроса (employer_id, если указан).
    """
    if employer_id is not None:
        return (
            """
            select
                id,
                company_name,
                description,
                email,
                created_at,
                updated_at,
                rating
            from
                la_employer
            where id = %s
            """,
            (employer_id,),  # Параметр для подстановки в SQL-запрос
        )
    else:
        return (
            """
            select
                *
            from
                la_employer
            """,
            (),  # Пустой кортеж параметров, так как запрос не требует параметров
        )

def get_import_history(import_history_id: int = None):
    """
    Возвращает SQL-запрос и параметры для получения данных об истории импорта.

    Args:
        import_history_id (int, optional): ID записи истории импорта. Если не указан, 
                                         возвращает запрос для всех записей истории импорта.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и параметры для выполнения запроса.
               - SQL-запрос (str): Запрос для выборки данных об истории импорта.
               - Параметры (tuple): Кортеж с параметрами для запроса (import_history_id, если указан).
    """
    if import_history_id is not None:
        return (
            """
            SELECT
                id,
                timestamp,
                data_type,
                file_name,
                records_count,
                status
            FROM
                la_df_import_history
            WHERE id = %s
            """,
            (import_history_id,),
        )
    else:
        return (
            """
            SELECT
                id,
                timestamp,
                data_type,
                file_name,
                records_count,
                status
            FROM
                la_df_import_history
            ORDER BY timestamp DESC
            """,
            (),
        )

def get_import_stats():
    """
    Возвращает SQL-запрос для получения статистики импорта.

    Returns:
        tuple: Кортеж, содержащий SQL-запрос и пустой кортеж параметров.
               - SQL-запрос (str): Запрос для выборки данных о статистике импорта.
               - Параметры (tuple): Пустой кортеж параметров.
    """
    return (
        """
        SELECT
            id,
            sum_of_imported_files,
            sum_of_imported_records,
            last_file_timestamp
        FROM
            la_df_import_stats
        """,
        (),
    )