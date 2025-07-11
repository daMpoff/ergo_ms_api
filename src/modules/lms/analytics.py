from django.db import models
from django.contrib.auth.models import User
from typing import Dict, Any

from .models import (
    Subject, Enrollment, Grade, Test, TestAttempt, Assignment,
    SubmittedAssignment, Forum, ForumPost, UserBadge
)

class AnalyticsService:
    """Сервис для аналитики и статистики"""
    
    @staticmethod
    def get_student_stats(user: User) -> Dict[str, Any]:
        """Получить статистику студента"""
        # Курсы
        enrolled_courses = Enrollment.objects.filter(student=user, status='active').count()
        completed_courses = Enrollment.objects.filter(student=user, status='completed').count()
        
        # Оценки
        grades = Grade.objects.filter(student=user)
        average_grade = grades.aggregate(models.Avg('grade'))['grade__avg'] or 0
        
        # Тесты
        test_attempts = TestAttempt.objects.filter(student=user)
        total_tests = test_attempts.count()
        passed_tests = test_attempts.filter(is_passed=True).count()
        
        # Задания
        submitted_assignments = SubmittedAssignment.objects.filter(student=user).count()
        
        # Значки и активность
        total_badges = UserBadge.objects.filter(user=user).count()
        forum_posts = ForumPost.objects.filter(author=user).count()
        
        return {
            'enrolled_courses': enrolled_courses,
            'completed_courses': completed_courses,
            'average_grade': round(average_grade, 2),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'submitted_assignments': submitted_assignments,
            'total_badges': total_badges,
            'forum_posts': forum_posts
        }
    
    @staticmethod
    def get_teacher_stats(user: User) -> Dict[str, Any]:
        """Получить статистику преподавателя"""
        subjects = Subject.objects.filter(teacher=user)
        
        # Студенты
        total_students = Enrollment.objects.filter(
            subject__in=subjects, status='active'
        ).values('student').distinct().count()
        
        # Средние оценки
        average_grades = Grade.objects.filter(
            subject__in=subjects
        ).aggregate(models.Avg('grade'))['grade__avg'] or 0
        
        # Активные тесты
        active_tests = Test.objects.filter(
            lesson__theme__subject__in=subjects, is_active=True
        ).count()
        
        # Задания на проверке
        pending_assignments = SubmittedAssignment.objects.filter(
            assignment__lesson__theme__subject__in=subjects, grade=0
        ).count()
        
        # Форумы
        forum_discussions = Forum.objects.filter(subject__in=subjects).count()
        
        # Выданные значки
        badges_awarded = UserBadge.objects.filter(
            badge__subject__in=subjects
        ).count()
        
        return {
            'total_students': total_students,
            'total_subjects': subjects.count(),
            'average_grades': round(average_grades, 2),
            'active_tests': active_tests,
            'pending_assignments': pending_assignments,
            'forum_discussions': forum_discussions,
            'badges_awarded': badges_awarded
        }
    
    @staticmethod
    def get_course_analytics(subject: Subject) -> Dict[str, Any]:
        """Получить аналитику по курсу"""
        enrollments = Enrollment.objects.filter(subject=subject)
        active_count = enrollments.filter(status='active').count()
        completed_count = enrollments.filter(status='completed').count()
        
        # Оценки
        grades = Grade.objects.filter(subject=subject)
        avg_grade = grades.aggregate(models.Avg('grade'))['grade__avg'] or 0
        
        # Прогресс
        avg_progress = enrollments.aggregate(
            models.Avg('progress_percentage')
        )['progress_percentage__avg'] or 0
        
        return {
            'active_students': active_count,
            'completed_students': completed_count,
            'average_grade': round(avg_grade, 2),
            'average_progress': round(avg_progress, 2),
            'completion_rate': round(
                (completed_count / (active_count + completed_count) * 100) 
                if (active_count + completed_count) > 0 else 0, 2
            )
        }


class ReportsService:
    """Сервис для генерации детальных отчетов"""
    
    @staticmethod
    def generate_performance_report(subject: Subject) -> Dict[str, Any]:
        """Генерация отчета по успеваемости курса"""
        students = Enrollment.objects.filter(
            subject=subject, status='active'
        ).select_related('student')
        
        report = []
        for enrollment in students:
            student = enrollment.student
            student_grades = Grade.objects.filter(
                student=student, subject=subject
            )
            avg_grade = student_grades.aggregate(
                models.Avg('grade')
            )['grade__avg'] or 0
            
            test_attempts = TestAttempt.objects.filter(
                student=student,
                test__lesson__theme__subject=subject
            )
            avg_test_score = test_attempts.aggregate(
                models.Avg('score')
            )['score__avg'] or 0
            
            report.append({
                'student_name': student.get_full_name() or student.username,
                'average_grade': round(avg_grade, 2),
                'average_test_score': round(avg_test_score, 2),
                'progress': enrollment.progress_percentage,
                'last_activity': enrollment.enrollment_date  # можно заменить на реальную активность
            })
        
        return {
            'subject': subject.name,
            'total_students': len(report),
            'students': report
        } 