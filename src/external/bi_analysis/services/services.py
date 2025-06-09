import csv
from uuid import uuid4
from django.db import connection
from rest_framework.exceptions import ValidationError
import pandas as pd

from ..bi_datasets.models import DataSetField, FileUpload, DataSetTable

def populate_initial_fields(dataset, temp_table_name, staging_table=None):
    """
    Создаёт DataSetField для каждой колонки temp_table_name с дефолтными type/aggregation.
    Если имя столбца вида <table>__<col> — ищет соответствующую DataSetTable.
    """
    cols = introspect_columns(temp_table_name)
    ds_tables = {t.table_name: t for t in DataSetTable.objects.filter(dataset=dataset)}
    objs = []

    for idx, col in enumerate(cols):
        source_tbl = None
        if '__' in col:
            tbl_name, _ = col.split('__', 1)
            source_tbl = ds_tables.get(tbl_name)
        else:
            # Без алиаса — поле из главной (первой) таблицы
            if staging_table:
                # staging_table может быть объектом, а не строкой
                # Если это объект, ищи по .table_name
                tbl_name = staging_table.table_name if hasattr(staging_table, 'table_name') else staging_table
                source_tbl = ds_tables.get(tbl_name)
            if not source_tbl:
                source_tbl = next(iter(ds_tables.values()), None)

        if not source_tbl:
            # Логируем и пропускаем — либо бросаем явную ошибку
            print(f"[WARNING] Не удалось найти source_table для колонки '{col}'")
            continue  # либо: raise ValueError(f"Can't resolve source_table for '{col}'")

        objs.append(DataSetField(
            dataset=dataset,
            name=col,
            source_table=source_tbl,
            source_column=col,
            order=idx
        ))
    DataSetField.objects.bulk_create(objs)

def create_temp_table_from_source(dataset):
    raw = dataset.table_ref
    if not raw:
        raise ValidationError("Не задано поле table_ref…")
    if '.' in raw:
        schema, table = raw.split('.', 1)
    else:
        schema, table = 'public', raw

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 0')
        temp_name = f"temp_{uuid4().hex}"
        cursor.execute(f'CREATE TABLE "{temp_name}" AS SELECT * FROM "{schema}"."{table}";')
    print(f"[CREATE TEMP] table_ref={dataset.table_ref}, temp_name={temp_name}")
    return temp_name

def import_file_upload_to_table(file_upload_id, dataset=None):
    upload  = FileUpload.objects.get(pk=file_upload_id)
    path    = upload.file.path
    staging = f"temp_{uuid4().hex}"

    mapping = {}
    if dataset is not None:
        fields = DataSetField.objects.filter(dataset=dataset)
        mapping = {f.source_column: f.name for f in fields if f.name != f.source_column}

    if upload.file_type == 'xlsx':
        df = pd.read_excel(path, header=0)
    elif upload.file_type in ('csv', 'txt'):
        with open(path, 'r', encoding='cp1251', errors='replace', newline='') as f:
            reader = csv.reader(f)
            rows   = list(reader)
        if not rows:
            raise ValidationError("Пустой файл")
        cols = rows[0]
        data = rows[1:]
        cols = [mapping.get(col, col) for col in cols]
        return _create_table_and_load(staging, cols, data)
    else:
        raise ValidationError(f"Неподдерживаемый тип файла: {upload.file_type}")

    if mapping:
        df = df.rename(columns=mapping)

    cols = list(df.columns.astype(str))
    data = df.fillna('').astype(str).values.tolist()
    return _create_table_and_load(staging, cols, data)


def _create_table_and_load(staging, cols, rows):
    """
    Общая логика: создаём staging-таблицу TEXT и массово вставляем rows.
    """
    col_defs = ", ".join(f'"{c}" TEXT' for c in cols)

    placeholders = ", ".join(["%s"] * len(cols))
    insert_sql   = f'''
        INSERT INTO "{staging}" ({", ".join(f'"{c}"' for c in cols)})
        VALUES ({placeholders})
    '''

    with connection.cursor() as cursor:
        cursor.execute(f'CREATE TABLE "{staging}" ({col_defs});')
        cursor.executemany(insert_sql, rows)

    return staging

def introspect_columns(temp_table_name):
    """
    Возвращает список (column_name, data_type) для временной таблицы.
    """
    safe_name = temp_table_name.replace('"', '""')
    sql = f'SELECT * FROM "{safe_name}" LIMIT 0;'
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [col[0] for col in cursor.description]
    
def table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", [table_name])
        exists = cursor.fetchone()[0] is not None
        print(f"[TABLE EXISTS] {table_name}: {exists}")
        return exists
    
def safe_drop_table(table_name):
    """
    Безопасно удаляет таблицу, если она есть.
    """
    with connection.cursor() as cursor:
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')

def auto_join_table(dataset, table, left_column, right_column, join_type='INNER JOIN'):
    dataset.refresh_from_db(fields=['table_ref'])
    print(f"[AUTOJOIN_DEBUG] dataset.id={dataset.id} table_ref={dataset.table_ref}")
    
    temp_name = dataset.table_ref

    # Всегда работаем только с последней временной таблицей
    if temp_name.endswith('_joined'):
        base_name = temp_name[:-7]
        joined_name = temp_name  # Уже суффикс есть — перезаписываем поверх
    else:
        base_name = temp_name
        joined_name = f"{base_name}_joined"

    safe_drop_table(joined_name)  # Удаляем, если есть

    if not table_exists(temp_name):
        raise ValueError(f"Временная таблица {temp_name} не существует, невозможно выполнить авто-JOIN.")

    # Проверяем наличие общих значений для ключей
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT DISTINCT "{left_column}" FROM "{temp_name}" LIMIT 5000')
        main_values = set(row[0] for row in cursor.fetchall())
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT DISTINCT "{right_column}" FROM "{table.table_name}" LIMIT 5000')
        table_values = set(row[0] for row in cursor.fetchall())

    common_values = main_values & table_values
    if not common_values:
        raise ValueError(
            f"Нет общих значений между столбцами '{left_column}' в таблицах '{temp_name}' и '{table.table_name}'. "
            f"JOIN невозможен. Проверьте содержимое."
        )

    # --- Генерируем уникальные алиасы ---
    main_cols = introspect_columns(temp_name)
    join_cols = introspect_columns(table.table_name)
    main_set = set(main_cols)
    all_aliases = set(main_cols)

    select_parts = []
    for col in main_cols:
        select_parts.append(f'a."{col}" AS "{col}"')

    for col in join_cols:
        alias = col
        if alias in all_aliases:
            # Подбираем уникальный алиас
            i = 1
            while f"{col}__right" + (f"_{i}" if i > 1 else "") in all_aliases:
                i += 1
            alias = f"{col}__right" + (f"_{i}" if i > 1 else "")
        all_aliases.add(alias)
        select_parts.append(f'b."{col}" AS "{alias}"')

    select_sql = ', '.join(select_parts)

    join_sql = f'''
        CREATE TABLE "{joined_name}" AS
        SELECT {select_sql}
        FROM "{temp_name}" a
        {join_type} "{table.table_name}" b ON a."{left_column}" = b."{right_column}";
    '''

    with connection.cursor() as cursor:
        cursor.execute(join_sql)

    dataset.table_ref = joined_name
    dataset.save(update_fields=["table_ref"])

    return left_column


def create_temp_table_from_staging(staging_name):
    """
    Создаёт temp_... таблицу на основе staging_... таблицы (по имени).
    """
    if '.' in staging_name:
        schema, table = staging_name.split('.', 1)
    else:
        schema, table = 'public', staging_name

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM \"{schema}\".\"{table}\" LIMIT 0')
        temp_name = f"temp_{uuid4().hex}"
        cursor.execute(f'CREATE TABLE \"{temp_name}\" AS SELECT * FROM \"{schema}\".\"{table}\";')
    print(f"[CREATE TEMP] staging={staging_name}, temp={temp_name}")
    return temp_name

def get_columns_with_aliases(left_table, right_table):
    # Получаем имена столбцов из обеих таблиц
    left_cols = introspect_columns(left_table)
    right_cols = introspect_columns(right_table)
    left_set = set(left_cols)
    columns = []

    # 1. Все из левой таблицы как есть
    columns += [f'a."{col}" AS "{col}"' for col in left_cols]
    # 2. Все из правой таблицы, если имя совпадает — алиасим
    for col in right_cols:
        if col in left_set:
            columns.append(f'b."{col}" AS "{col}__right"')
        else:
            columns.append(f'b."{col}" AS "{col}"')
    return columns


