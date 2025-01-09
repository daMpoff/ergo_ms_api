ERGO MS

Установка проекта (Windows):
1. py -3.12 -m venv .venv
2. call .venv\Scripts\activate
3. pip install poetry
4. poetry config virtualenvs.in-project true
5. poetry install
6. mkdir media
7. mkdir logs
8. poetry run collectstatic