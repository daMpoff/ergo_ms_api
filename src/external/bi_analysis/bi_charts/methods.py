from django.db import connection
from psycopg2 import sql

PG_NUMERIC = {
    'smallint', 'integer', 'bigint',
    'decimal', 'numeric', 'real', 'double precision'
}
PG_DATE = {'date', 'timestamp', 'timestamp without time zone',
           'timestamp with time zone', 'time', 'time without time zone'}

SAMPLE = 100

def _probe_type(table: str, column: str) -> str:
    patt_num  = r'^[0-9]+(\.[0-9]+)?$'
    patt_date = r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$|^[0-9]{2}\.[0-9]{2}\.[0-9]{4}$'

    with connection.cursor() as cur:
        # 1) numeric?
        cur.execute(
            sql.SQL("SELECT COUNT(*) FROM {} WHERE {} !~ %s LIMIT %s")
               .format(sql.Identifier(table), sql.Identifier(column)),
            [patt_num, SAMPLE]
        )
        if cur.fetchone()[0] == 0:
            return 'number'

        # 2) date?
        cur.execute(
            sql.SQL("SELECT COUNT(*) FROM {} WHERE {} !~ %s LIMIT %s")
               .format(sql.Identifier(table), sql.Identifier(column)),
            [patt_date, SAMPLE]
        )
        if cur.fetchone()[0] == 0:
            return 'date'

    return 'string'


def fetch_columns_and_types(table_name: str):
    sql = """
        SELECT column_name, data_type
          FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = %s
         ORDER BY ordinal_position
    """
    with connection.cursor() as cur:
        cur.execute(sql, [table_name])
        rows = cur.fetchall()

    cols = []
    for name, pg_type in rows:
        if pg_type in PG_NUMERIC:
            t = 'number'
        elif pg_type in PG_DATE:
            t = 'date'
        elif pg_type == 'text':
            t = _probe_type(table_name, name)
        else:
            t = 'string'

        cols.append({"name": name, "pg_type": pg_type, "type": t})
    return cols


def get_rows_for_chart(pk):
    """
    Получить все строки итоговой (временной) таблицы для выбранного чарта/dataset.
    :param pk: ID чарта/датасета
    :return: Список словарей — строки итоговой таблицы
    """
    from src.external.bi_analysis.bi_datasets.models import Dataset
    dataset = Dataset.objects.get(pk=pk)
    table_name = dataset.table_ref

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 10000')
        columns = [col[0] for col in cursor.description]
        result = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    return result