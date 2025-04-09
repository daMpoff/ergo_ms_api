import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

def clean_data(data):
    """
    Преобразует список словарей в DataFrame и удаляет строки с пустыми значениями.
    """
    df = pd.DataFrame(data)
    df = df.dropna()
    return df

def detect_outliers(df):
    """
    Обнаруживает выбросы с помощью Isolation Forest.
    Возвращает список индексов выбросов.
    """
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if numeric_cols.empty:
        return []

    model = IsolationForest(contamination=0.05, random_state=42)
    preds = model.fit_predict(df[numeric_cols])

    outliers = df[preds == -1]
    return outliers.to_dict(orient='records')

def normalize_data(df):
    """
    Нормализует числовые значения с помощью StandardScaler.
    Возвращает список словарей с нормализованными значениями.
    """
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if numeric_cols.empty:
        return df.to_dict(orient='records')

    scaler = StandardScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    return df.to_dict(orient='records')