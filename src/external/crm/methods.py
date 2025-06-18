from django.db import connection
from datetime import datetime, timedelta

# Создавайте свои вспомогательные методы здесь

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

def get_project_completion_stats():
    """
    Статистика завершенности проектов
    Показывает процент выполнения задач по каждому проекту
    """
    query = """
    SELECT 
        p.name AS project_name,
        p.id AS project_id,
        COUNT(t.id) AS total_tasks,
        SUM(CASE WHEN t.isdone = TRUE THEN 1 ELSE 0 END) AS completed_tasks,
        CASE 
            WHEN COUNT(t.id) > 0 THEN 
                ROUND((SUM(CASE WHEN t.isdone = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(t.id)), 2)
            ELSE 0 
        END AS completion_percentage,
        p.deadline AS project_deadline
    FROM crm_project p
    LEFT JOIN crm_section s ON s.project_id = p.id
    LEFT JOIN crm_task t ON t.section_id = s.id
    GROUP BY p.id, p.name, p.deadline
    ORDER BY completion_percentage DESC, p.name
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
        print(f"Error in get_project_completion_stats: {str(e)}")
        raise

def get_user_productivity_stats():
    """
    Статистика продуктивности пользователей
    Показывает количество выполненных и невыполненных задач по пользователям
    """
    query = """
    SELECT 
        u.username,
        u.id AS user_id,
        COUNT(t.id) AS total_tasks,
        SUM(CASE WHEN t.isdone = TRUE THEN 1 ELSE 0 END) AS completed_tasks,
        SUM(CASE WHEN t.isdone = FALSE THEN 1 ELSE 0 END) AS pending_tasks,
        CASE 
            WHEN COUNT(t.id) > 0 THEN 
                ROUND((SUM(CASE WHEN t.isdone = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(t.id)), 2)
            ELSE 0 
        END AS completion_rate
    FROM auth_user u
    LEFT JOIN crm_task t ON t.user_id = u.id
    GROUP BY u.id, u.username
    HAVING COUNT(t.id) > 0
    ORDER BY completion_rate DESC, completed_tasks DESC
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
        print(f"Error in get_user_productivity_stats: {str(e)}")
        raise

def get_deadline_analysis():
    """
    Анализ дедлайнов задач
    Показывает количество просроченных, критических и будущих задач
    """
    query = """
    SELECT 
        CASE 
            WHEN t.deadline < CURRENT_DATE AND t.isdone = FALSE THEN 'overdue'
            WHEN t.deadline BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' AND t.isdone = FALSE THEN 'critical'
            WHEN t.deadline > CURRENT_DATE + INTERVAL '7 days' AND t.isdone = FALSE THEN 'future'
            WHEN t.isdone = TRUE THEN 'completed'
            ELSE 'no_deadline'
        END AS deadline_status,
        COUNT(*) AS tasks_count
    FROM crm_task t
    GROUP BY 
        CASE 
            WHEN t.deadline < CURRENT_DATE AND t.isdone = FALSE THEN 'overdue'
            WHEN t.deadline BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' AND t.isdone = FALSE THEN 'critical'
            WHEN t.deadline > CURRENT_DATE + INTERVAL '7 days' AND t.isdone = FALSE THEN 'future'
            WHEN t.isdone = TRUE THEN 'completed'
            ELSE 'no_deadline'
        END
    ORDER BY 
        CASE 
            CASE 
                WHEN t.deadline < CURRENT_DATE AND t.isdone = FALSE THEN 'overdue'
                WHEN t.deadline BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' AND t.isdone = FALSE THEN 'critical'
                WHEN t.deadline > CURRENT_DATE + INTERVAL '7 days' AND t.isdone = FALSE THEN 'future'
                WHEN t.isdone = TRUE THEN 'completed'
                ELSE 'no_deadline'
            END
            WHEN 'overdue' THEN 1
            WHEN 'critical' THEN 2
            WHEN 'future' THEN 3
            WHEN 'completed' THEN 4
            WHEN 'no_deadline' THEN 5
        END
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
        print(f"Error in get_deadline_analysis: {str(e)}")
        raise

def get_task_creation_trend():
    """
    Тренд создания задач по дням за последние 30 дней
    """
    query = """
    SELECT 
        DATE(dateofcreation) AS creation_date,
        COUNT(*) AS tasks_created
    FROM crm_task
    WHERE dateofcreation >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(dateofcreation)
    ORDER BY creation_date
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
        print(f"Error in get_task_creation_trend: {str(e)}")
        raise

def get_project_timeline_stats():
    """
    Статистика временных рамок проектов
    Показывает проекты с их временными характеристиками
    """
    query = """
    SELECT 
        p.name AS project_name,
        p.dateofcreation AS project_start,
        p.deadline AS project_deadline,
        COUNT(t.id) AS total_tasks,
        SUM(CASE WHEN t.isdone = TRUE THEN 1 ELSE 0 END) AS completed_tasks,
        CASE 
            WHEN p.deadline < CURRENT_DATE THEN 'overdue'
            WHEN p.deadline BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' THEN 'critical'
            WHEN p.deadline > CURRENT_DATE + INTERVAL '7 days' THEN 'on_track'
        END AS project_status,
        CASE 
            WHEN COUNT(t.id) > 0 THEN 
                ROUND((SUM(CASE WHEN t.isdone = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(t.id)), 2)
            ELSE 0 
        END AS completion_percentage
    FROM crm_project p
    LEFT JOIN crm_section s ON s.project_id = p.id
    LEFT JOIN crm_task t ON t.section_id = s.id
    GROUP BY p.id, p.name, p.dateofcreation, p.deadline
    ORDER BY p.deadline ASC
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
        print(f"Error in get_project_timeline_stats: {str(e)}")
        raise

def get_calendar_activity_stats():
    """
    Статистика активности календаря
    Показывает распределение событий календаря по дням недели и времени
    """
    query = """
    SELECT 
        EXTRACT(DOW FROM time) AS day_of_week,
        CASE 
            WHEN EXTRACT(DOW FROM time) = 0 THEN 'Воскресенье'
            WHEN EXTRACT(DOW FROM time) = 1 THEN 'Понедельник'
            WHEN EXTRACT(DOW FROM time) = 2 THEN 'Вторник'
            WHEN EXTRACT(DOW FROM time) = 3 THEN 'Среда'
            WHEN EXTRACT(DOW FROM time) = 4 THEN 'Четверг'
            WHEN EXTRACT(DOW FROM time) = 5 THEN 'Пятница'
            WHEN EXTRACT(DOW FROM time) = 6 THEN 'Суббота'
        END AS day_name,
        COUNT(*) AS events_count,
        EXTRACT(HOUR FROM time) AS hour_of_day
    FROM crm_calendar
    GROUP BY EXTRACT(DOW FROM time), EXTRACT(HOUR FROM time)
    ORDER BY day_of_week, hour_of_day
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
        print(f"Error in get_calendar_activity_stats: {str(e)}")
        raise

def get_task_complexity_stats():
    """
    Статистика сложности задач (на основе приоритета и наличия подзадач)
    """
    query = """
    SELECT 
        t.priority,
        COUNT(CASE WHEN subtasks.parent_count > 0 THEN 1 END) AS tasks_with_subtasks,
        COUNT(CASE WHEN subtasks.parent_count = 0 OR subtasks.parent_count IS NULL THEN 1 END) AS simple_tasks,
        COUNT(*) AS total_tasks,
        AVG(CASE WHEN t.isdone = TRUE THEN 
            DATE_PART('day', CURRENT_DATE - t.dateofcreation)
            ELSE NULL END) AS avg_completion_days
    FROM crm_task t
    LEFT JOIN (
        SELECT 
            parenttask_id,
            COUNT(*) as parent_count
        FROM crm_task 
        WHERE parenttask_id IS NOT NULL
        GROUP BY parenttask_id
    ) subtasks ON subtasks.parenttask_id = t.id
    GROUP BY t.priority
    ORDER BY t.priority
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
        print(f"Error in get_task_complexity_stats: {str(e)}")
        raise