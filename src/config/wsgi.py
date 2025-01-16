"""
Файл содержит конфигурацию для WSGI-приложения Django.

Он устанавливает переменную окружения DJANGO_SETTINGS_MODULE на 'src.config.patterns.development',
что указывает Django, какие настройки использовать для этого окружения. Затем создает WSGI-приложение
с помощью функции get_wsgi_application из django.core.wsgi.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.config.patterns.development')

application = get_wsgi_application()