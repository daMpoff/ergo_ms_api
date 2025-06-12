import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

logger = logging.getLogger(__name__)

def handle_db_errors(func):
    """Декоратор для обработки ошибок БД"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper

def get_table_info(cursor, table_name):
    """Получает информацию о конкретной таблице"""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, [table_name])
    return cursor.fetchall()

def check_table_exists(cursor, table_name):
    """Проверяет существование таблицы"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = %s
        )
    """, [table_name])
    return cursor.fetchone()[0]

def check_sequence_exists(cursor, sequence_name):
    """Проверяет существование последовательности"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM pg_sequences 
            WHERE sequencename = %s AND schemaname = 'public'
        )
    """, [sequence_name])
    return cursor.fetchone()[0]

@handle_db_errors
def get_tables_info(cursor):
    """
    Получает информацию о всех таблицах аналитического модуля.
    Возвращает список таблиц с количеством колонок и записей.
    """
    try:
        # Получаем список таблиц с количеством колонок
        cursor.execute("""
            WITH table_info AS (
                SELECT 
                    t.table_name,
                    COUNT(c.column_name) as column_count
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c 
                    ON c.table_name = t.table_name 
                    AND c.table_schema = 'public'
                WHERE t.table_schema = 'public'
                    AND t.table_name LIKE 'la_%%'
                GROUP BY t.table_name
            )
            SELECT table_name, column_count
            FROM table_info;
        """)
        
        tables_info = cursor.fetchall()
        result_tables = []
        
        # Для каждой таблицы получаем количество записей
        for table in tables_info:
            table_name = table[0]
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cursor.fetchone()[0]
            result_tables.append({
                'name': table_name,
                'columns_count': table[1],
                'rows_count': row_count
            })
        
        return result_tables
    except Exception as e:
        logger.error(f"Error in get_tables_info: {str(e)}")
        raise

@handle_db_errors
def clear_analytics_tables(cursor):
    """Очистка всех таблиц аналитического модуля и сброс всех последовательностей"""
    try:
        # Шаг 1: Получаем список всех таблиц с префиксом la_
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'la_%'
        """)
        tables = [table[0] for table in cursor.fetchall()]
        
        logger.info(f"Всего таблиц для очистки: {len(tables)}. Список: {tables}")
        
        # Отключаем проверку внешних ключей временно для ускорения операции
        cursor.execute("SET session_replication_role = 'replica'")
        
        cleared_tables = []
        reset_sequences = []
        
        # Шаг 2: Очищаем каждую таблицу с CASCADE, чтобы очистить связанные данные
        for table in tables:
            try:
                # Очищаем таблицу со всеми зависимостями
                cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                cleared_tables.append(table)
                logger.info(f"Таблица {table} очищена")
            except Exception as e:
                logger.error(f"Ошибка при очистке таблицы {table}: {str(e)}")
        
        # Шаг 3: Получаем список ВСЕХ последовательностей в базе данных
        cursor.execute("""
            SELECT sequencename 
            FROM pg_sequences 
            WHERE schemaname = 'public'
        """)
        
        all_sequences = [seq[0] for seq in cursor.fetchall()]
        logger.info(f"Всего последовательностей в базе: {len(all_sequences)}")
        
        # Шаг 4: Используем короткие имена последовательностей, определенные в моделях
        specific_sequences = [
            # Короткие имена последовательностей, определенные в моделях
            "la_df_speciality_id_seq",
            "la_df_curriculum_id_seq",
            "la_df_technology_id_seq",
            "la_df_competency_id_seq",
            "la_df_base_discipline_id_seq",
            "la_df_discipline_id_seq",
            "la_df_vacancy_id_seq",
            "la_df_academic_competence_matrix_id_seq",
            "la_df_competency_profile_of_vacancy_id_seq",
            "la_df_user_competency_matrix_id_seq",
            "la_employer_id_seq",
            
            # Для m2m таблиц
            "la_df_disc_tech_rel_id_seq",
            "la_df_disc_comp_rel_id_seq",
            "la_df_vacancy_tech_rel_id_seq",
            "la_df_vacancy_comp_rel_id_seq",
            "la_df_vcm_tech_rel_id_seq",
            "la_df_vcm_comp_rel_id_seq"
        ]
        
        # Фильтруем, чтобы оставить только существующие последовательности
        sequences_to_reset = []
        for seq in specific_sequences:
            if check_sequence_exists(cursor, seq):
                sequences_to_reset.append(seq)
                logger.info(f"Найдена последовательность: {seq}")
            else:
                logger.warning(f"Последовательность не найдена: {seq}")
        
        # Также ищем дополнительные последовательности, связанные с нашим модулем,
        # на случай, если в базе остались старые длинные имена последовательностей
        for seq in all_sequences:
            if (seq.startswith('la_') or 'learning_analytics' in seq) and seq not in sequences_to_reset:
                sequences_to_reset.append(seq)
                logger.info(f"Найдена дополнительная последовательность: {seq}")
        
        logger.info(f"Всего последовательностей для сброса: {len(sequences_to_reset)}. Список: {sequences_to_reset}")
        
        # Шаг 5: Сбрасываем все найденные последовательности
        for sequence in sequences_to_reset:
            try:
                cursor.execute(f"ALTER SEQUENCE {sequence} RESTART WITH 1")
                reset_sequences.append(sequence)
                logger.info(f"Последовательность {sequence} сброшена")
            except Exception as e:
                logger.error(f"Ошибка при сбросе последовательности {sequence}: {str(e)}")
        
        # Шаг 6: Убеждаемся, что все последовательности точно сброшены
        for sequence in sequences_to_reset:
            try:
                # Дополнительный способ сброса последовательности
                cursor.execute(f"SELECT setval('{sequence}', 1, false)")
                logger.info(f"Дополнительно сброшена последовательность {sequence}")
            except Exception as e:
                logger.error(f"Ошибка при дополнительном сбросе {sequence}: {str(e)}")
        
        # Включаем обратно проверку внешних ключей
        cursor.execute("SET session_replication_role = DEFAULT")
        
        # Возвращаем результаты очистки
        return {
            'cleared_tables': cleared_tables,
            'reset_sequences': reset_sequences,
            'message': f"Очищено {len(cleared_tables)} таблиц и сброшено {len(reset_sequences)} последовательностей"
        }
    except Exception as e:
        logger.error(f"Ошибка при очистке таблиц: {str(e)}")
        # Убедимся, что ограничения включены обратно даже при ошибке
        try:
            cursor.execute("SET session_replication_role = DEFAULT")
        except:
            pass
        raise e