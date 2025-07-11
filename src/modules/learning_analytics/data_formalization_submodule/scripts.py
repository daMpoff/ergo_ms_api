import json
import string

def get_import_history(import_history_id: int = None):
    """Получение данных о истории импорта"""
    if import_history_id is not None:
        return (
            "SELECT * FROM la_df_import_history WHERE id = %s",
            (import_history_id,)
        )
    return ("SELECT * FROM la_df_import_history", ())

def get_import_stats():
    """Получение данных о статистике импорта"""
    return ("SELECT * FROM la_df_import_stats", ())


def get_specialities(speciality_id: int = None):
    """Получение данных о специальностях"""
    if speciality_id is not None:
        return (
            "SELECT * FROM la_df_speciality WHERE id = %s",
            (speciality_id,)
        )
    return ("SELECT * FROM la_df_speciality", ())

def get_curriculum(curriculum_id: int = None):
    """Получение данных о учебных планах"""
    if curriculum_id is not None:
        return (
            "SELECT * FROM la_df_curriculum WHERE id = %s",
            (curriculum_id,)
        )
    return ("SELECT * FROM la_df_curriculum", ())

def get_technologies(technology_id: int = None):
    """Получение данных о технологиях"""
    if technology_id is not None:
        return (
            "SELECT * FROM la_df_technology WHERE id = %s",
            (technology_id,)
        )
    return ("SELECT * FROM la_df_technology", ())

def get_competentions(competency_id: int = None):
    """Получение данных о компетенциях"""
    if competency_id is not None:
        return (
            "SELECT * FROM la_df_competency WHERE id = %s",
            (competency_id,)
        )
    return ("SELECT * FROM la_df_competency", ())

def get_base_disciplines(base_discipline_id: int = None):
    """Получение данных о базовых дисциплинах"""
    if base_discipline_id is not None:
        return (
            "SELECT * FROM la_df_base_discipline WHERE id = %s",
            (base_discipline_id,)
        )
    return ("SELECT * FROM la_df_base_discipline", ())

def get_disciplines(discipline_id: int = None):
    """Получение данных о дисциплинах"""
    if discipline_id is not None:
        return (
            "SELECT * FROM la_df_discipline WHERE id = %s",
            (discipline_id,)
        )
    return ("SELECT * FROM la_df_discipline", ())

def get_vacancies(vacancy_id: int = None):
    """Получение данных о вакансиях"""
    if vacancy_id is not None:
        return (
            "SELECT * FROM la_df_vacancy WHERE id = %s",
            (vacancy_id,)
        )
    return ("SELECT * FROM la_df_vacancy", ())

def get_academicCompetenceMatrix(matrix_id: int = None):
    """Получение данных о матрицах академических компетенций"""
    if matrix_id is not None:
        return (
            "SELECT * FROM la_df_academic_competence_matrix WHERE id = %s",
            (matrix_id,)
        )
    return ("SELECT * FROM la_df_academic_competence_matrix", ())

def get_competencyProfileOfVacancy(cp_id: int = None, employer_id: int = None):
    """Получение данных о профилях компетенций вакансий"""
    if cp_id is not None:
        return (
            "SELECT * FROM la_df_competency_profile_of_vacancy WHERE id = %s",
            (cp_id,)
        )
    elif employer_id is not None:
        return (
            "SELECT * FROM la_df_competency_profile_of_vacancy WHERE employer_id = %s",
            (employer_id,)
        )
    return ("SELECT * FROM la_df_competency_profile_of_vacancy", ())

def get_userCompetenceMatrix(matrix_id: int = None):
    """Получение данных о матрицах компетенций пользователей"""
    if matrix_id is not None:
        return (
            "SELECT * FROM la_df_user_competency_matrix WHERE id = %s",
            (matrix_id,)
        )
    return ("SELECT * FROM la_df_user_competency_matrix", ())

def get_discipline_technology_relations(discipline_id: int = None, technology_id: int = None):
    """Получение связей между дисциплинами и технологиями"""
    base_query = """
        SELECT d.id as discipline_id, d.name as discipline_name,
               t.id as technology_id, t.name as technology_name
        FROM la_df_discipline d
        JOIN la_df_disc_tech_rel dtr ON d.id = dtr.discipline_id
        JOIN la_df_technology t ON t.id = dtr.technology_id
    """
    if discipline_id is not None:
        return (f"{base_query} WHERE d.id = %s", (discipline_id,))
    elif technology_id is not None:
        return (f"{base_query} WHERE t.id = %s", (technology_id,))
    return (base_query, ())

def get_discipline_competency_relations(discipline_id: int = None, competency_id: int = None):
    """Получение связей между дисциплинами и компетенциями"""
    base_query = """
        SELECT d.id as discipline_id, d.name as discipline_name,
               c.id as competency_id, c.name as competency_name
        FROM la_df_discipline d
        JOIN la_df_disc_comp_rel dcr ON d.id = dcr.discipline_id
        JOIN la_df_competency c ON c.id = dcr.competency_id
    """
    if discipline_id is not None:
        return (f"{base_query} WHERE d.id = %s", (discipline_id,))
    elif competency_id is not None:
        return (f"{base_query} WHERE c.id = %s", (competency_id,))
    return (base_query, ())

def get_vacancy_technology_relations(vacancy_id: int = None, technology_id: int = None):
    """Получение связей между вакансиями и технологиями"""
    base_query = """
        SELECT v.id as vacancy_id, v.title as vacancy_title,
               t.id as technology_id, t.name as technology_name
        FROM la_df_vacancy v
        JOIN la_df_vacancy_tech_rel vtr ON v.id = vtr.vacancy_id
        JOIN la_df_technology t ON t.id = vtr.technology_id
    """
    if vacancy_id is not None:
        return (f"{base_query} WHERE v.id = %s", (vacancy_id,))
    elif technology_id is not None:
        return (f"{base_query} WHERE t.id = %s", (technology_id,))
    return (base_query, ())

def get_vacancy_competency_relations(vacancy_id: int = None, competency_id: int = None):
    """Получение связей между вакансиями и компетенциями"""
    base_query = """
        SELECT v.id as vacancy_id, v.title as vacancy_title,
               c.id as competency_id, c.name as competency_name
        FROM la_df_vacancy v
        JOIN la_df_vacancy_comp_rel vcr ON v.id = vcr.vacancy_id
        JOIN la_df_competency c ON c.id = vcr.competency_id
    """
    if vacancy_id is not None:
        return (f"{base_query} WHERE v.id = %s", (vacancy_id,))
    elif competency_id is not None:
        return (f"{base_query} WHERE c.id = %s", (competency_id,))
    return (base_query, ())

def get_vcm_technology_relations(vcm_id: int = None, technology_id: int = None):
    """Получение связей между профилями вакансий и технологиями"""
    base_query = """
        SELECT vcm.id as vcm_id, v.title as vacancy_title,
               t.id as technology_id, t.name as technology_name
        FROM la_df_competency_profile_of_vacancy vcm
        JOIN la_df_vacancy v ON vcm.vacancy_id = v.id
        JOIN la_df_vcm_tech_rel vcmtr ON vcm.id = vcmtr.vcm_id
        JOIN la_df_technology t ON t.id = vcmtr.technology_id
    """
    if vcm_id is not None:
        return (f"{base_query} WHERE vcm.id = %s", (vcm_id,))
    elif technology_id is not None:
        return (f"{base_query} WHERE t.id = %s", (technology_id,))
    return (base_query, ())

def get_vcm_competency_relations(vcm_id: int = None, competency_id: int = None):
    """Получение связей между профилями вакансий и компетенциями"""
    base_query = """
        SELECT vcm.id as vcm_id, v.title as vacancy_title,
               c.id as competency_id, c.name as competency_name
        FROM la_df_competency_profile_of_vacancy vcm
        JOIN la_df_vacancy v ON vcm.vacancy_id = v.id
        JOIN la_df_vcm_comp_rel vcmcr ON vcm.id = vcmcr.vcm_id
        JOIN la_df_competency c ON c.id = vcmcr.competency_id
    """
    if vcm_id is not None:
        return (f"{base_query} WHERE vcm.id = %s", (vcm_id,))
    elif competency_id is not None:
        return (f"{base_query} WHERE c.id = %s", (competency_id,))
    return (base_query, ())

# Новые функции для подсчета количества записей в таблицах

def get_acm_count():
    """Подсчет количества записей в таблице матриц академических компетенций"""
    return ("SELECT COUNT(*) FROM la_df_academic_competence_matrix", ())

def get_vcm_count():
    """Подсчет количества записей в таблице профилей компетенций вакансий"""
    return ("SELECT COUNT(*) FROM la_df_competency_profile_of_vacancy", ())

def get_vcm_tech_rel_count():
    """Подсчет количества связей между профилями компетенций вакансий и технологиями"""
    return ("SELECT COUNT(*) FROM la_df_vcm_tech_rel", ())

def get_vcm_comp_rel_count():
    """Подсчет количества связей между профилями компетенций вакансий и компетенциями"""
    return ("SELECT COUNT(*) FROM la_df_vcm_comp_rel", ())