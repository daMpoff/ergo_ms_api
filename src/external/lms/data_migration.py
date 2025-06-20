# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from src.external.lms.models import CourseFormat

def create_default_course_formats():
    """Создает стандартные форматы курсов"""
    default_formats = [
        {
            'name': 'Темы',
            'description': 'Курс организован по темам с разделами',
            'is_active': True
        },
        {
            'name': 'Недели',
            'description': 'Курс организован по неделям с хронологической структурой',
            'is_active': True
        },
        {
            'name': 'Социальный формат',
            'description': 'Курс с акцентом на социальное взаимодействие',
            'is_active': True
        },
        {
            'name': 'Одна активность',
            'description': 'Курс состоит из одной основной активности',
            'is_active': True
        },
        {
            'name': 'Проектный формат',
            'description': 'Курс организован вокруг выполнения проектов',
            'is_active': True
        }
    ]
    
    for format_data in default_formats:
        format_obj, created = CourseFormat.objects.get_or_create(
            name=format_data['name'],
            defaults=format_data
        )
        if created:
            print(f"Создан формат курса: {format_obj.name}")
        else:
            print(f"Формат курса уже существует: {format_obj.name}")

if __name__ == '__main__':
    create_default_course_formats() 