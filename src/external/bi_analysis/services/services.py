import csv
from uuid import uuid4
from django.db import connection, transaction
from rest_framework.exceptions import ValidationError
import pandas as pd
from io import StringIO

from ..bi_datasets.models import DataSetField, DataSetTable, FileUpload

def populate_initial_fields(dataset, temp_table_name, source_table=None):
    """
    Создаёт DataSetField для каждой колонки temp_table_name с дефолтными type/aggregation.
    Если указан source_table, будет проставлен у создаваемых полей.
    """
    cols = introspect_columns(temp_table_name)
    objs = []

    for idx, col in enumerate(cols):
        objs.append(DataSetField(
            dataset=dataset,
            name=col,
            source_table=source_table,
            source_column=col,
            order=idx
        ))

    DataSetField.objects.bulk_create(objs)

def create_temp_table_from_source(dataset):
    raw = dataset.table_ref
    if getattr(dataset, 'file_upload', None):
        path = dataset.file_upload.file.path
        return temp_name
    
    raw = dataset.table_ref
    if not raw:
        raise ValidationError("Не задано поле table_ref…")
    if not raw:
        raise ValidationError("Не задано поле table_ref, невозможно создать временную таблицу")
    if '.' in raw:
        schema, table = raw.split('.', 1)
    else:
        schema, table = 'public', raw

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 0')
        temp_name = f"temp_{uuid4().hex}"
        cursor.execute(f'CREATE TABLE "{temp_name}" AS SELECT * FROM "{schema}"."{table}";')
    return temp_name

def import_file_upload_to_table(file_upload_id, dataset=None):
    upload  = FileUpload.objects.get(pk=file_upload_id)
    path    = upload.file.path
    staging = f"staging_{uuid4().hex}"

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
    sql = f"SELECT * FROM {temp_table_name} LIMIT 0;"
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [col[0] for col in cursor.description]

def auto_join_table(dataset, table):
    """
    При добавлении DataSetTable — ищет общий столбец по имени и
    делает ALTER или Re-create temp_table с джойном.
    """
    temp_name = f"temp_dataset_{dataset.id}"
    existing_cols = set(introspect_columns(temp_name))
    new_cols      = set(introspect_columns(table.table_name))
    common        = existing_cols & new_cols
    if not common:
        raise ValueError("Не найдено общих полей для авто-JOIN")
    key = common.pop()
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE TABLE {temp_name}_new AS ...')
        cursor.execute(f'ALTER TABLE {temp_name} RENAME TO {temp_name}_old;')
        cursor.execute(f'ALTER TABLE {temp_name}_new RENAME TO {temp_name};')
        cursor.execute(f'DROP TABLE {temp_name}_old;')