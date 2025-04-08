import json
import pandas as pd
from openpyxl import load_workbook

def auto_parse_uploaded_file(file):
    filename = file.name.lower()

    if filename.endswith('.csv'):
        df = pd.read_csv(file)
        return df.to_dict(orient='records')

    elif filename.endswith('.json'):
        return json.load(file)

    elif filename.endswith('.xlsx'):
        df = pd.read_excel(file)
        return df.to_dict(orient='records')

    raise ValueError("Формат файла не поддерживается. Используйте CSV, JSON или XLSX.")