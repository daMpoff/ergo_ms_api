from django.db import connection

def get_expert_system_metrics():
    """
    Основные метрики экспертной системы для SystemMetricsCard
    """
    query = """
    SELECT 
        'students' as metric_type,
        COUNT(*) as total_count,
        SUM(CASE WHEN has_experience = TRUE THEN 1 ELSE 0 END) as with_experience,
        SUM(CASE WHEN role_id IS NOT NULL THEN 1 ELSE 0 END) as with_role
    FROM expert_system_expertsystemstudentprofile
    
    UNION ALL
    
    SELECT 
        'companies' as metric_type,
        COUNT(*) as total_count,
        SUM(CASE WHEN is_verified = TRUE THEN 1 ELSE 0 END) as verified,
        0 as with_role
    FROM expert_system_expertsystemcompanyprofile
    
    UNION ALL
    
    SELECT 
        'skills' as metric_type,
        COUNT(*) as total_count,
        0 as verified,
        0 as with_role
    FROM expert_system_expertsystemskill
    
    UNION ALL
    
    SELECT 
        'tests' as metric_type,
        COUNT(*) as total_count,
        0 as verified,
        0 as with_role
    FROM expert_system_expertsystemtest
    
    UNION ALL
    
    SELECT 
        'vacancies' as metric_type,
        COUNT(*) as total_count,
        0 as verified,
        0 as with_role
    FROM expert_system_expertsystemvacancy
    
    UNION ALL
    
    SELECT 
        'user_skills' as metric_type,
        COUNT(*) as total_count,
        SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
        0 as with_role
    FROM expert_system_expertsystemuserskill
    
    UNION ALL
    
    SELECT 
        'test_results' as metric_type,
        COUNT(*) as total_count,
        SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END) as passed,
        0 as with_role
    FROM expert_system_expertsystemtestresult
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
        print(f"Error in get_expert_system_metrics: {str(e)}")
        raise

def get_skills_analytics():
    """
    Детальная аналитика навыков - исправленная версия для PostgreSQL
    """
    query = """
    SELECT 
        s.id as skill_id,
        s.name as skill_name,
        COALESCE(COUNT(DISTINCT us.id), 0) as total_users,
        COALESCE(SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END), 0) as confirmed_users,
        COALESCE(SUM(CASE WHEN us.status = 'unconfirmed' THEN 1 ELSE 0 END), 0) as unconfirmed_users,
        COALESCE(COUNT(DISTINCT t.id), 0) as test_count,
        COALESCE(COUNT(DISTINCT tr.id), 0) as test_attempts,
        COALESCE(SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END), 0) as test_passes,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND(CAST(COALESCE(AVG(tr.score), 0) AS NUMERIC), 2)
            ELSE 0 
        END as avg_test_score,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND(CAST((COALESCE(SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END), 0) * 100.0 / COUNT(DISTINCT tr.id)) AS NUMERIC), 2)
            ELSE 0 
        END as success_rate
    FROM expert_system_expertsystemskill s
    LEFT JOIN expert_system_expertsystemuserskill us ON us.skill_id = s.id
    LEFT JOIN expert_system_expertsystemtest t ON t.skill_id = s.id
    LEFT JOIN expert_system_expertsystemtestresult tr ON tr.test_id = t.id
    GROUP BY s.id, s.name
    ORDER BY total_users DESC, confirmed_users DESC
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                # Обрабатываем каждую строку и заменяем None на 0
                processed_row = []
                for value in row:
                    if value is None:
                        processed_row.append(0)
                    else:
                        processed_row.append(value)
                
                results.append(dict(zip(columns, processed_row)))
            
            print(f"Skills analytics: found {len(results)} skills")  # Отладка
            return results
            
    except Exception as e:
        print(f"Error in get_skills_analytics: {str(e)}")
        import traceback
        traceback.print_exc()
        # Возвращаем пустой список вместо исключения
        return []

def get_popular_skills(limit=10):
    """
    Популярные навыки - исправленная версия для PostgreSQL
    """
    query = """
    SELECT 
        s.id as skill_id,
        s.name as skill_name,
        COALESCE(COUNT(DISTINCT us.id), 0) as total_users,
        COALESCE(SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END), 0) as confirmed_users,
        COALESCE(SUM(CASE WHEN us.status = 'unconfirmed' THEN 1 ELSE 0 END), 0) as unconfirmed_users,
        CASE WHEN COUNT(DISTINCT t.id) > 0 THEN TRUE ELSE FALSE END as has_test,
        COALESCE(COUNT(DISTINCT tr.id), 0) as test_attempts,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND(CAST((COALESCE(SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END), 0) * 100.0 / COUNT(DISTINCT tr.id)) AS NUMERIC), 1)
            ELSE 0 
        END as success_rate,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND(CAST(COALESCE(AVG(tr.score), 0) AS NUMERIC), 1)
            ELSE 0 
        END as avg_score,
        (COALESCE(SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END), 0) * 2 + COALESCE(COUNT(DISTINCT us.id), 0)) as popularity_score
    FROM expert_system_expertsystemskill s
    LEFT JOIN expert_system_expertsystemuserskill us ON us.skill_id = s.id
    LEFT JOIN expert_system_expertsystemtest t ON t.skill_id = s.id
    LEFT JOIN expert_system_expertsystemtestresult tr ON tr.test_id = t.id
    GROUP BY s.id, s.name
    ORDER BY popularity_score DESC, confirmed_users DESC, s.name ASC
    LIMIT %s
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, [limit])
            columns = [col[0] for col in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                # Обрабатываем каждую строку и заменяем None на 0
                processed_row = []
                for value in row:
                    if value is None:
                        processed_row.append(0)
                    else:
                        processed_row.append(value)
                
                results.append(dict(zip(columns, processed_row)))
            
            print(f"Popular skills: found {len(results)} skills")  # Отладка
            for skill in results[:3]:  # Показываем первые 3 для отладки
                print(f"  - {skill['skill_name']}: {skill['total_users']} users")
            
            return results
            
    except Exception as e:
        print(f"Error in get_popular_skills: {str(e)}")
        import traceback
        traceback.print_exc()
        # Возвращаем пустой список вместо исключения
        return []

def get_test_results_analytics():
    """
    Аналитика результатов тестов - исправленная версия для PostgreSQL
    """
    check_query = "SELECT COUNT(*) FROM expert_system_expertsystemtestresult"
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(check_query)
            count = cursor.fetchone()[0]
            print(f"Test results count: {count}")
            
            if count == 0:
                # Если нет данных, возвращаем структуру с нулями
                return {
                    'total_attempts': 0,
                    'passed_attempts': 0,
                    'failed_attempts': 0,
                    'average_score': 0.0,
                    'success_rate': 0.0,
                    'score_90_100': 0,
                    'score_80_89': 0,
                    'score_70_79': 0,
                    'score_60_69': 0,
                    'score_below_60': 0,
                    'unique_tests': 0,
                    'unique_users': 0
                }
            
            # Если данные есть, выполняем основной запрос с исправленным ROUND
            main_query = """
            SELECT 
                COALESCE(COUNT(*), 0) as total_attempts,
                COALESCE(SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END), 0) as passed_attempts,
                COALESCE(SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END), 0) as failed_attempts,
                ROUND(CAST(COALESCE(AVG(score), 0) AS NUMERIC), 2) as average_score,
                CASE 
                    WHEN COUNT(*) > 0 THEN 
                        ROUND(CAST((COALESCE(SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END), 0) * 100.0 / COUNT(*)) AS NUMERIC), 2)
                    ELSE 0.0 
                END as success_rate,
                COALESCE(SUM(CASE WHEN score >= 90 THEN 1 ELSE 0 END), 0) as score_90_100,
                COALESCE(SUM(CASE WHEN score >= 80 AND score < 90 THEN 1 ELSE 0 END), 0) as score_80_89,
                COALESCE(SUM(CASE WHEN score >= 70 AND score < 80 THEN 1 ELSE 0 END), 0) as score_70_79,
                COALESCE(SUM(CASE WHEN score >= 60 AND score < 70 THEN 1 ELSE 0 END), 0) as score_60_69,
                COALESCE(SUM(CASE WHEN score < 60 THEN 1 ELSE 0 END), 0) as score_below_60,
                COALESCE(COUNT(DISTINCT test_id), 0) as unique_tests,
                COALESCE(COUNT(DISTINCT user_id), 0) as unique_users
            FROM expert_system_expertsystemtestresult
            """
            
            cursor.execute(main_query)
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if row:
                # Обрабатываем результат и заменяем None на 0
                processed_row = []
                for value in row:
                    if value is None:
                        processed_row.append(0)
                    else:
                        processed_row.append(value)
                
                result = dict(zip(columns, processed_row))
                print(f"Test analytics result: {result}")  # Отладка
                return result
            else:
                # Если по какой-то причине нет результата
                return {
                    'total_attempts': 0,
                    'passed_attempts': 0,
                    'failed_attempts': 0,
                    'average_score': 0.0,
                    'success_rate': 0.0,
                    'score_90_100': 0,
                    'score_80_89': 0,
                    'score_70_79': 0,
                    'score_60_69': 0,
                    'score_below_60': 0,
                    'unique_tests': 0,
                    'unique_users': 0
                }
                
    except Exception as e:
        print(f"Error in get_test_results_analytics: {str(e)}")
        import traceback
        traceback.print_exc()
        # Возвращаем структуру с нулями вместо исключения
        return {
            'total_attempts': 0,
            'passed_attempts': 0,
            'failed_attempts': 0,
            'average_score': 0.0,
            'success_rate': 0.0,
            'score_90_100': 0,
            'score_80_89': 0,
            'score_70_79': 0,
            'score_60_69': 0,
            'score_below_60': 0,
            'unique_tests': 0,
            'unique_users': 0
        }

def get_students_stats():
    """
    Статистика студентов для StudentsStatsCard - исправленная версия для PostgreSQL
    """
    query = """
    SELECT 
        -- Общая статистика студентов
        COUNT(*) as total_students,
        SUM(CASE WHEN has_experience = TRUE THEN 1 ELSE 0 END) as students_with_experience,
        SUM(CASE WHEN role_id IS NOT NULL THEN 1 ELSE 0 END) as students_with_role,
        
        -- Статистика по навыкам студентов
        (SELECT COUNT(DISTINCT us.user_id) 
         FROM expert_system_expertsystemuserskill us 
         WHERE us.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
        ) as students_with_skills,
        
        (SELECT COUNT(*) 
         FROM expert_system_expertsystemuserskill us 
         WHERE us.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
           AND us.status = 'confirmed'
        ) as confirmed_skills_count,
        
        (SELECT COUNT(*) 
         FROM expert_system_expertsystemuserskill us 
         WHERE us.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
           AND us.status = 'unconfirmed'
        ) as unconfirmed_skills_count,
        
        -- Статистика по тестированию
        (SELECT COUNT(DISTINCT tr.user_id) 
         FROM expert_system_expertsystemtestresult tr 
         WHERE tr.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
        ) as students_tested,
        
        (SELECT COUNT(*) 
         FROM expert_system_expertsystemtestresult tr 
         WHERE tr.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
        ) as total_test_attempts,
        
        (SELECT COUNT(*) 
         FROM expert_system_expertsystemtestresult tr 
         WHERE tr.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
           AND tr.passed = TRUE
        ) as passed_tests,
        
        -- Средний балл студентов с CAST для PostgreSQL
        (SELECT ROUND(CAST(COALESCE(AVG(tr.score), 0) AS NUMERIC), 2)
         FROM expert_system_expertsystemtestresult tr 
         WHERE tr.user_id IN (SELECT id FROM expert_system_expertsystemstudentprofile)
        ) as average_score
        
    FROM expert_system_expertsystemstudentprofile
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if row:
                # Обрабатываем результат и заменяем None на 0
                processed_row = []
                for value in row:
                    if value is None:
                        processed_row.append(0)
                    else:
                        processed_row.append(value)
                
                result = dict(zip(columns, processed_row))
                
                # Вычисляем дополнительные метрики
                total_students = result['total_students']
                if total_students > 0:
                    result['experience_percentage'] = round((result['students_with_experience'] * 100.0 / total_students), 1)
                    result['role_selection_percentage'] = round((result['students_with_role'] * 100.0 / total_students), 1)
                    result['test_activity_percentage'] = round((result['students_tested'] * 100.0 / total_students), 1)
                    
                    # Дополнительные поля для компонента
                    result['active_in_tests'] = result['students_tested']
                    result['avg_skills_per_student'] = round((result['confirmed_skills_count'] + result['unconfirmed_skills_count']) / total_students, 1) if total_students > 0 else 0
                    result['avg_confirmed_skills'] = round(result['confirmed_skills_count'] / total_students, 1) if total_students > 0 else 0
                    result['avg_tests_per_student'] = round(result['total_test_attempts'] / total_students, 1) if total_students > 0 else 0
                else:
                    result['experience_percentage'] = 0
                    result['role_selection_percentage'] = 0
                    result['test_activity_percentage'] = 0
                    result['active_in_tests'] = 0
                    result['avg_skills_per_student'] = 0
                    result['avg_confirmed_skills'] = 0
                    result['avg_tests_per_student'] = 0
                
                # Вычисляем процент успешности тестов
                total_attempts = result['total_test_attempts']
                if total_attempts > 0:
                    result['test_success_rate'] = round((result['passed_tests'] * 100.0 / total_attempts), 1)
                else:
                    result['test_success_rate'] = 0
                
                print(f"Students stats result: {result}")  # Отладка
                return result
            else:
                # Если по какой-то причине нет результата
                return create_empty_students_stats()
                
    except Exception as e:
        print(f"Error in get_students_stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_empty_students_stats()

def create_empty_students_stats():
    """
    Создает пустую структуру данных для статистики студентов
    """
    return {
        'total_students': 0,
        'students_with_experience': 0,
        'students_with_role': 0,
        'students_with_skills': 0,
        'confirmed_skills_count': 0,
        'unconfirmed_skills_count': 0,
        'students_tested': 0,
        'total_test_attempts': 0,
        'passed_tests': 0,
        'average_score': 0.0,
        'experience_percentage': 0,
        'role_selection_percentage': 0,
        'test_activity_percentage': 0,
        'test_success_rate': 0,
        'active_in_tests': 0,
        'avg_skills_per_student': 0,
        'avg_confirmed_skills': 0,
        'avg_tests_per_student': 0
    }

def get_testing_data():
    """
    Данные для аналитики тестирования - новая функция
    """
    query = """
    SELECT 
        tr.id as result_id,
        tr.score,
        tr.passed,
        sp.first_name,
        sp.last_name,
        sp.study_group_id,
        sg.name as group_name,
        t.name as test_name,
        s.name as skill_name,
        s.id as skill_id,
        t.id as test_id
    FROM expert_system_expertsystemtestresult tr
    JOIN expert_system_expertsystemstudentprofile sp ON tr.user_id = sp.id
    LEFT JOIN expert_system_expertsystemstudygroup sg ON sp.study_group_id = sg.id
    JOIN expert_system_expertsystemtest t ON tr.test_id = t.id
    JOIN expert_system_expertsystemskill s ON t.skill_id = s.id
    ORDER BY tr.id DESC
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                # Обрабатываем каждую строку
                processed_row = []
                for value in row:
                    if value is None:
                        processed_row.append('')
                    else:
                        processed_row.append(value)
                
                result_dict = dict(zip(columns, processed_row))
                
                # Форматируем данные для фронтенда
                result_dict['student_name'] = f"{result_dict['first_name']} {result_dict['last_name']}"
                result_dict['group_display'] = result_dict['group_name'] or 'Без группы'
                
                results.append(result_dict)
            
            print(f"Testing data: found {len(results)} records")
            return results
            
    except Exception as e:
        print(f"Error in get_testing_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return []