from django.db import connection
from datetime import datetime

def get_tasks_by_month(year=None, month=None):
    query = """
    SELECT 
        EXTRACT(YEAR FROM dateofcreation) AS year,
        EXTRACT(MONTH FROM dateofcreation) AS month,
        COUNT(*) AS total_tasks,
        SUM(CASE WHEN isdone = TRUE THEN 1 ELSE 0 END) AS completed_tasks,
        SUM(CASE WHEN isdone = FALSE AND deadline IS NOT NULL AND deadline > NOW() THEN 1 ELSE 0 END) AS in_progress_tasks,
        SUM(CASE WHEN isdone = FALSE AND (deadline IS NULL OR deadline <= NOW()) THEN 1 ELSE 0 END) AS pending_tasks
    FROM crm_task
    """
    
    where_conditions = []
    params = []
    
    if year is not None:
        where_conditions.append("EXTRACT(YEAR FROM dateofcreation) = %s")
        params.append(year)
    
    if month is not None:
        where_conditions.append("EXTRACT(MONTH FROM dateofcreation) = %s")
        params.append(month)
    
    if where_conditions:
        query += " WHERE " + " AND ".join(where_conditions)
    
    query += """
    GROUP BY 
        EXTRACT(YEAR FROM dateofcreation),
        EXTRACT(MONTH FROM dateofcreation)
    ORDER BY 
        year, month
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    
    return results

def get_tasks_by_priority():
    """
    Возвращает статистику задач, сгруппированных по приоритетам,
    с разбивкой на выполненные и невыполненные
    """
    query = """
    SELECT 
        priority,
        SUM(CASE WHEN isdone = TRUE THEN 1 ELSE 0 END) AS completed_tasks,
        SUM(CASE WHEN isdone = FALSE THEN 1 ELSE 0 END) AS pending_tasks,
        COUNT(*) AS total_tasks
    FROM crm_task
    GROUP BY priority
    ORDER BY priority
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    
    return results

def get_tasks_by_section():
    """
    Возвращает статистику задач, сгруппированных по секциям,
    с подсчетом общего количества задач в каждой секции
    """
    query = """
    SELECT 
        s.name AS section_name,
        COUNT(t.id) AS tasks_count
    FROM crm_section s
    LEFT JOIN crm_task t ON t.section_id = s.id
    GROUP BY s.id, s.name
    ORDER BY s.name
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
            return results
    except Exception as e:
        print(f"Error in get_tasks_by_section: {str(e)}")
        raise