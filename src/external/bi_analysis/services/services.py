import csv
from uuid import uuid4
from django.db import connection, transaction
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

def auto_join_table(dataset, table, left_column, right_column,
                    join_type: str = "INNER JOIN"):

    dataset.refresh_from_db(fields=["table_ref"])
    src_name   = dataset.table_ref              # текущая temp- или *_joined
    base_name  = src_name[:-7] if src_name.endswith("_joined") else src_name
    target_name = f"{base_name}_joined"         # то имя, на которое хотим выйти
    work_name   = f"{target_name}_{uuid4().hex[:6]}"  # временное, чтобы не конфликтовать

    # 1. Проверяем, что источник существует
    if not table_exists(src_name):
        raise ValueError(f"Таблица {src_name} не найдена, JOIN невозможен")

    # 2. Собираем DISTINCT-значения, чтобы убедиться, что JOIN имеет смысл
    with connection.cursor() as c:
        c.execute(f'SELECT DISTINCT "{left_column}" FROM "{src_name}" LIMIT 5000')
        main_vals = {r[0] for r in c.fetchall()}
        c.execute(f'SELECT DISTINCT "{right_column}" FROM "{table.table_name}" LIMIT 5000')
        join_vals = {r[0] for r in c.fetchall()}

    if not (main_vals & join_vals):
        raise ValueError("Нет общих значений; авто-JOIN прерван")

    # 3. Формируем SELECT-часть
    main_cols = introspect_columns(src_name)
    join_cols = introspect_columns(table.table_name)
    aliases   = set(main_cols)
    select_sql = []

    select_sql += [f'a."{col}" AS "{col}"' for col in main_cols]

    for col in join_cols:
        alias = col
        while alias in aliases:
            alias = f"{alias}__right"
        aliases.add(alias)
        select_sql.append(f'b."{col}" AS "{alias}"')

    select_clause = ", ".join(select_sql)

    # 4. Создаём новую таблицу с уникальным именем
    create_sql = f'''
        CREATE TABLE "{work_name}" AS
        SELECT {select_clause}
        FROM "{src_name}"  a
        {join_type} "{table.table_name}" b
              ON a."{left_column}" = b."{right_column}";
    '''

    # 5. Меняем таблицы в одной транзакции
    with transaction.atomic():
        with connection.cursor() as c:
            c.execute(create_sql)                 # создаём new
            safe_drop_table(target_name)          # дроп старую  *_joined
            c.execute(f'ALTER TABLE "{work_name}" RENAME TO "{target_name}";')

    # 6. Обновляем dataset
    dataset.table_ref = target_name
    dataset.save(update_fields=["table_ref"])

    return left_column

def rebuild_dataset_joins(dataset):
    """
    Полностью перестраивает temp_<…>_joined от нуля:
    1.  Берёт главную temp-таблицу (joined_on is NULL).
    2.  Ставит её в dataset.table_ref.
    3.  Идёт по оставшимся DataSetTable-ам (joined_on ≠ NULL) в порядке id
        и последовательно вызывает auto_join_table().
    """
    from .services import auto_join_table, safe_drop_table

    base_tbl = dataset.tables.filter(joined_on_type__isnull=True).first()
    if not base_tbl:
        raise ValueError("Не найдена главная таблица")

    # 1. Чистим старый *_joined
    if dataset.table_ref and dataset.table_ref.endswith("_joined"):
        safe_drop_table(dataset.table_ref)

    dataset.table_ref = base_tbl.table_name
    dataset.save(update_fields=["table_ref"])

    # 2. Достраиваем остальные JOIN-ы заново
    for t in (
        dataset.tables.filter(joined_on_type__isnull=False)
        .order_by("id")            # либо по order, если он есть
    ):
        auto_join_table(
            dataset,
            t,
            t.joined_on_left,
            t.joined_on_right,
            t.joined_on_type or "INNER JOIN",
        )

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


