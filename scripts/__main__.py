import os

def run_makemigrations():
    os.system("python src/manage.py makemigrations")

def run_migrate():
    os.system("python src/manage.py migrate")

def run_dev():
    os.system("python src/manage.py runserver")

def run_shell():
    os.system("python src/manage.py shell")

def run_prod():
    os.system("python src/manage.py start_daphne")

def run_stop_prod():
    os.system("python src/manage.py stop_daphne")

def run_clear_cache():
    os.system("python src/manage.py clear_cache")

def run_clear_pycache():
    os.system("python src/manage.py clear_pycache")

def run_collectstatic():
    os.system("python src/manage.py collectstatic")