from django.db import connection

def get_expert_system_metrics():
    """
    Основные метрики экспертной системы для SystemMetricsCard
    Адаптировано под существующие модели
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
    Детальная аналитика навыков для SkillsAnalyticsCard
    Адаптировано под существующие модели
    """
    query = """
    SELECT 
        s.id as skill_id,
        s.name as skill_name,
        COUNT(DISTINCT us.id) as total_users,
        SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_users,
        SUM(CASE WHEN us.status = 'unconfirmed' THEN 1 ELSE 0 END) as unconfirmed_users,
        COUNT(DISTINCT t.id) as test_count,
        COUNT(DISTINCT tr.id) as test_attempts,
        SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END) as test_passes,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND(AVG(tr.score), 2)
            ELSE 0 
        END as avg_test_score,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND((SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT tr.id)), 2)
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
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
            return results
    except Exception as e:
        print(f"Error in get_skills_analytics: {str(e)}")
        raise

def get_popular_skills(limit=10):
    """
    Популярные навыки для PopularSkillsCard
    Адаптировано под существующие модели
    """
    query = """
    SELECT 
        s.id as skill_id,
        s.name as skill_name,
        COUNT(DISTINCT us.id) as total_users,
        SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_users,
        SUM(CASE WHEN us.status = 'unconfirmed' THEN 1 ELSE 0 END) as unconfirmed_users,
        CASE WHEN COUNT(DISTINCT t.id) > 0 THEN TRUE ELSE FALSE END as has_test,
        COUNT(DISTINCT tr.id) as test_attempts,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND((SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT tr.id)), 1)
            ELSE 0 
        END as success_rate,
        CASE 
            WHEN COUNT(DISTINCT tr.id) > 0 THEN 
                ROUND(AVG(tr.score), 1)
            ELSE 0 
        END as avg_score,
        (SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END) * 2 + COUNT(DISTINCT us.id)) as popularity_score
    FROM expert_system_expertsystemskill s
    LEFT JOIN expert_system_expertsystemuserskill us ON us.skill_id = s.id
    LEFT JOIN expert_system_expertsystemtest t ON t.skill_id = s.id
    LEFT JOIN expert_system_expertsystemtestresult tr ON tr.test_id = t.id
    GROUP BY s.id, s.name
    HAVING COUNT(DISTINCT us.id) > 0
    ORDER BY popularity_score DESC, confirmed_users DESC
    LIMIT %s
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, [limit])
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
            return results
    except Exception as e:
        print(f"Error in get_popular_skills: {str(e)}")
        raise

def get_students_overview():
    """
    Обзор студентов для StudentsOverviewCard
    Адаптировано под существующие модели (без created_at)
    """
    query = """
    WITH student_stats AS (
        SELECT 
            sp.id as student_id,
            sp.first_name,
            sp.last_name,
            sp.has_experience,
            sp.role_id,
            sg.name as group_name,
            sg.id as group_id,
            COUNT(DISTINCT us.id) as skills_count,
            COUNT(DISTINCT CASE WHEN us.status = 'confirmed' THEN us.id END) as confirmed_skills,
            COUNT(DISTINCT tr.id) as tests_taken,
            COUNT(DISTINCT CASE WHEN tr.passed = TRUE THEN tr.id END) as tests_passed
        FROM expert_system_expertsystemstudentprofile sp
        LEFT JOIN expert_system_expertsystemstudygroup sg ON sg.id = sp.study_group_id
        LEFT JOIN expert_system_expertsystemuserskill us ON us.user_id = sp.id
        LEFT JOIN expert_system_expertsystemtestresult tr ON tr.user_id = sp.id
        GROUP BY sp.id, sp.first_name, sp.last_name, sp.has_experience, sp.role_id, sg.name, sg.id
    )
    SELECT 
        COUNT(*) as total_students,
        SUM(CASE WHEN has_experience = TRUE THEN 1 ELSE 0 END) as students_with_experience,
        SUM(CASE WHEN role_id IS NOT NULL THEN 1 ELSE 0 END) as students_with_role,
        SUM(CASE WHEN tests_taken > 0 THEN 1 ELSE 0 END) as active_in_tests,
        ROUND(AVG(skills_count), 1) as avg_skills_per_student,
        ROUND(AVG(confirmed_skills), 1) as avg_confirmed_skills,
        ROUND(AVG(tests_taken), 1) as avg_tests_per_student,
        ROUND((SUM(CASE WHEN has_experience = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1) as experience_percentage,
        ROUND((SUM(CASE WHEN role_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1) as role_selection_percentage,
        ROUND((SUM(CASE WHEN tests_taken > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1) as test_activity_percentage
    FROM student_stats
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, cursor.fetchone()))
            return result
    except Exception as e:
        print(f"Error in get_students_overview: {str(e)}")
        raise

def get_student_groups_stats():
    """
    Статистика по группам студентов
    """
    query = """
    SELECT 
        sg.id as group_id,
        sg.name as group_name,
        COUNT(sp.id) as total_students,
        SUM(CASE WHEN sp.has_experience = TRUE THEN 1 ELSE 0 END) as with_experience,
        SUM(CASE WHEN sp.has_experience = FALSE THEN 1 ELSE 0 END) as without_experience,
        SUM(CASE WHEN sp.role_id IS NOT NULL THEN 1 ELSE 0 END) as with_role,
        COUNT(DISTINCT tr.user_id) as active_in_tests,
        ROUND(AVG(CASE WHEN skill_stats.total_skills > 0 
                       THEN (skill_stats.confirmed_skills * 100.0 / skill_stats.total_skills) 
                       ELSE 0 END), 1) as avg_progress
    FROM expert_system_expertsystemstudygroup sg
    LEFT JOIN expert_system_expertsystemstudentprofile sp ON sp.study_group_id = sg.id
    LEFT JOIN expert_system_expertsystemtestresult tr ON tr.user_id = sp.id
    LEFT JOIN (
        SELECT 
            us.user_id,
            COUNT(*) as total_skills,
            SUM(CASE WHEN us.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_skills
        FROM expert_system_expertsystemuserskill us
        GROUP BY us.user_id
    ) skill_stats ON skill_stats.user_id = sp.id
    GROUP BY sg.id, sg.name
    HAVING COUNT(sp.id) > 0
    ORDER BY total_students DESC
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
        print(f"Error in get_student_groups_stats: {str(e)}")
        raise

def get_companies_vacancies_stats():
    """
    Статистика компаний и вакансий для CompaniesVacanciesCard
    """
    query = """
    SELECT 
        cp.id as company_id,
        cp.company_name,
        cp.description,
        cp.contact_person,
        cp.is_verified,
        COUNT(DISTINCT v.id) as vacancy_count,
        COUNT(DISTINCT ca.id) as application_count,
        STRING_AGG(DISTINCT s.name, ', ' ORDER BY s.name) as required_skills,
        COUNT(DISTINCT vs.skill_id) as unique_skills_required
    FROM expert_system_expertsystemcompanyprofile cp
    LEFT JOIN expert_system_expertsystemvacancy v ON v.employer_id = cp.id
    LEFT JOIN expert_system_expertsystemcandidateapplication ca ON ca.vacancy_id = v.id
    LEFT JOIN expert_system_expertsystemvacancyskill vs ON vs.vacancy_id = v.id
    LEFT JOIN expert_system_expertsystemskill s ON s.id = vs.skill_id
    GROUP BY cp.id, cp.company_name, cp.description, cp.contact_person, cp.is_verified
    ORDER BY vacancy_count DESC, application_count DESC
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
        print(f"Error in get_companies_vacancies_stats: {str(e)}")
        raise

def get_popular_vacancy_skills():
    """
    Популярные навыки в вакансиях
    """
    query = """
    SELECT 
        s.id as skill_id,
        s.name as skill_name,
        COUNT(DISTINCT vs.vacancy_id) as vacancy_count,
        COUNT(DISTINCT v.employer_id) as company_count,
        SUM(CASE WHEN vs.is_mandatory = TRUE THEN 1 ELSE 0 END) as mandatory_count,
        ROUND((COUNT(DISTINCT vs.vacancy_id) * 100.0 / (
            SELECT COUNT(*) FROM expert_system_expertsystemvacancy
        )), 1) as percentage_of_vacancies
    FROM expert_system_expertsystemskill s
    JOIN expert_system_expertsystemvacancyskill vs ON vs.skill_id = s.id
    JOIN expert_system_expertsystemvacancy v ON v.id = vs.vacancy_id
    GROUP BY s.id, s.name
    ORDER BY vacancy_count DESC, company_count DESC
    LIMIT 10
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
        print(f"Error in get_popular_vacancy_skills: {str(e)}")
        raise

def get_test_results_analytics():
    """
    Аналитика результатов тестов для TestResultsCard
    """
    query = """
    SELECT 
        COUNT(*) as total_attempts,
        SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END) as passed_attempts,
        SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END) as failed_attempts,
        ROUND(AVG(score), 2) as average_score,
        ROUND((SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as success_rate,
        SUM(CASE WHEN score >= 90 THEN 1 ELSE 0 END) as score_90_100,
        SUM(CASE WHEN score >= 80 AND score < 90 THEN 1 ELSE 0 END) as score_80_89,
        SUM(CASE WHEN score >= 70 AND score < 80 THEN 1 ELSE 0 END) as score_70_79,
        SUM(CASE WHEN score >= 60 AND score < 70 THEN 1 ELSE 0 END) as score_60_69,
        SUM(CASE WHEN score < 60 THEN 1 ELSE 0 END) as score_below_60,
        COUNT(DISTINCT test_id) as unique_tests,
        COUNT(DISTINCT user_id) as unique_users
    FROM expert_system_expertsystemtestresult
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, cursor.fetchone()))
            return result
    except Exception as e:
        print(f"Error in get_test_results_analytics: {str(e)}")
        raise

def get_difficult_tests():
    """
    Сложные тесты с низкой успеваемостью
    """
    query = """
    SELECT 
        t.id as test_id,
        t.name as test_name,
        s.name as skill_name,
        COUNT(tr.id) as total_attempts,
        SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END) as passed_attempts,
        ROUND(AVG(tr.score), 1) as avg_score,
        ROUND((SUM(CASE WHEN tr.passed = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(tr.id)), 1) as pass_rate
    FROM expert_system_expertsystemtest t
    JOIN expert_system_expertsystemskill s ON s.id = t.skill_id
    JOIN expert_system_expertsystemtestresult tr ON tr.test_id = t.id
    GROUP BY t.id, t.name, s.name
    HAVING COUNT(tr.id) >= 3
    ORDER BY pass_rate ASC, avg_score ASC
    LIMIT 5
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
        print(f"Error in get_difficult_tests: {str(e)}")
        raise

def get_student_activity_timeline(days=30):
    """
    Активность студентов по дням (используем applied_at из заявок вместо created_at)
    """
    query = """
    WITH date_series AS (
        SELECT generate_series(
            CURRENT_DATE - INTERVAL '%s days',
            CURRENT_DATE,
            '1 day'::interval
        )::date AS activity_date
    ),
    application_activity AS (
        SELECT 
            DATE(applied_at) as activity_date,
            COUNT(*) as applications_count
        FROM expert_system_expertsystemcandidateapplication
        WHERE applied_at >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY DATE(applied_at)
    ),
    orientation_activity AS (
        SELECT 
            DATE(taken_at) as activity_date,
            COUNT(*) as orientation_tests_count
        FROM expert_system_expertsystemorientationtestresult
        WHERE taken_at >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY DATE(taken_at)
    )
    SELECT 
        ds.activity_date,
        COALESCE(aa.applications_count, 0) as applications_count,
        COALESCE(oa.orientation_tests_count, 0) as orientation_tests_count,
        COALESCE(aa.applications_count, 0) + COALESCE(oa.orientation_tests_count, 0) as total_activity
    FROM date_series ds
    LEFT JOIN application_activity aa ON aa.activity_date = ds.activity_date
    LEFT JOIN orientation_activity oa ON oa.activity_date = ds.activity_date
    ORDER BY ds.activity_date
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, [days, days, days])
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
            return results
    except Exception as e:
        print(f"Error in get_student_activity_timeline: {str(e)}")
        raise

def get_role_popularity_stats():
    """
    Популярность профессиональных ролей среди студентов
    """
    query = """
    SELECT 
        r.id as role_id,
        r.name as role_name,
        r.description,
        COUNT(sp.id) as students_count,
        ROUND((COUNT(sp.id) * 100.0 / (
            SELECT COUNT(*) FROM expert_system_expertsystemstudentprofile WHERE role_id IS NOT NULL
        )), 1) as percentage,
        SUM(CASE WHEN sp.has_experience = TRUE THEN 1 ELSE 0 END) as experienced_students,
        COUNT(DISTINCT c.id) as courses_available
    FROM expert_system_expertsystemrole r
    LEFT JOIN expert_system_expertsystemstudentprofile sp ON sp.role_id = r.id
    LEFT JOIN expert_system_expertsystemcourse c ON c.role_id = r.id
    GROUP BY r.id, r.name, r.description
    HAVING COUNT(sp.id) > 0
    ORDER BY students_count DESC
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
        print(f"Error in get_role_popularity_stats: {str(e)}")
        raise

def get_expert_system_dashboard_summary():
    """
    Сводка всех ключевых метрик для главного дашборда
    """
    query = """
    SELECT 
        'expert_system_summary' as report_type,
        (SELECT COUNT(*) FROM expert_system_expertsystemstudentprofile) as total_students,
        (SELECT COUNT(*) FROM expert_system_expertsystemcompanyprofile) as total_companies,
        (SELECT COUNT(*) FROM expert_system_expertsystemvacancy) as total_vacancies,
        (SELECT COUNT(*) FROM expert_system_expertsystemskill) as total_skills,
        (SELECT COUNT(*) FROM expert_system_expertsystemtest) as total_tests,
        (SELECT COUNT(*) FROM expert_system_expertsystemtestresult) as total_test_results,
        (SELECT COUNT(*) FROM expert_system_expertsystemuserskill WHERE status = 'confirmed') as confirmed_skills,
        (SELECT COUNT(*) FROM expert_system_expertsystemcandidateapplication) as total_applications,
        (SELECT ROUND(AVG(score), 1) FROM expert_system_expertsystemtestresult) as avg_test_score,
        (SELECT ROUND((COUNT(CASE WHEN passed = TRUE THEN 1 END) * 100.0 / COUNT(*)), 1) 
         FROM expert_system_expertsystemtestresult) as test_success_rate,
        (SELECT ROUND((COUNT(CASE WHEN is_verified = TRUE THEN 1 END) * 100.0 / COUNT(*)), 1) 
         FROM expert_system_expertsystemcompanyprofile) as company_verification_rate
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, cursor.fetchone()))
            return result
    except Exception as e:
        print(f"Error in get_expert_system_dashboard_summary: {str(e)}")
        raise