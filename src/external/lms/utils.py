from django.db.models import Q
from django.utils import timezone
from typing import List, Dict, Any


def get_user_accessible_subjects(user):
    """Получить курсы, доступные пользователю"""
    from .models import Subject
    
    user_roles = user.roles.values_list('role', flat=True)
    
    if 'admin' in user_roles:
        return Subject.objects.all()
    elif 'teacher' in user_roles or hasattr(user, 'teacher'):
        return Subject.objects.filter(
            Q(teacher=user) | Q(is_published=True)
        ).distinct()
    else:
        return Subject.objects.filter(is_published=True)


def format_file_size(size_bytes):
    """Форматировать размер файла в человекочитаемый формат"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def check_user_permission(user, permission_type, obj=None):
    """Проверить права пользователя"""
    user_roles = user.roles.values_list('role', flat=True)
    
    if 'admin' in user_roles:
        return True
    
    if permission_type == 'create_course' and 'teacher' in user_roles:
        return True
    
    if permission_type == 'edit_course' and obj:
        return obj.teacher == user or 'teacher' in user_roles
    
    return False


def get_upcoming_deadlines(user, days=7):
    """Получить предстоящие дедлайны"""
    from .models import Assignment, CalendarEvent
    from datetime import timedelta
    
    end_date = timezone.now() + timedelta(days=days)
    
    # Задания
    assignments = Assignment.objects.filter(
        lesson__theme__subject__enrollment__student=user,
        deadline__gte=timezone.now(),
        deadline__lte=end_date
    ).order_by('deadline')
    
    # События календаря
    events = CalendarEvent.objects.filter(
        subject__enrollment__student=user,
        start_date__gte=timezone.now(),
        start_date__lte=end_date
    ).order_by('start_date')
    
    return {
        'assignments': assignments,
        'events': events
    }


class ValidationMixin:
    """Миксин с общими методами валидации"""
    
    @staticmethod
    def validate_date_range(start_date, end_date):
        """Валидация диапазона дат"""
        if start_date and end_date and start_date >= end_date:
            raise ValueError('Дата начала должна быть раньше даты окончания')
    
    @staticmethod
    def validate_positive_integer(value, field_name):
        """Валидация положительного числа"""
        if value is not None and value <= 0:
            raise ValueError(f'{field_name} должно быть положительным числом')
    
    @staticmethod
    def validate_percentage(value, field_name):
        """Валидация процентного значения"""
        if value is not None and (value < 0 or value > 100):
            raise ValueError(f'{field_name} должно быть от 0 до 100') 