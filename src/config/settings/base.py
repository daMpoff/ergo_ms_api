"""
Файл содержащий базовую конфигурацию для Django-приложения.
Он включает настройки базового каталога проекта.
"""

from pathlib import Path

"""
Определяет базовый каталог проекта.

BASE_DIR используется для построения путей к различным ресурсам проекта, таким как шаблоны, статические файлы и т.д.
"""
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SYSTEM_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent