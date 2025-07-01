from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from datetime import timedelta
from typing import List, Dict, Any
import json

from .models import (
    Subject, Enrollment, Grade, Test, TestAttempt, Assignment,
    SubmittedAssignment, Badge, UserBadge, Notification,
    CalendarEvent, Forum, ForumPost, UserProfile
)


class NotificationService:
    """Сервис для управления уведомлениями"""
    
    @staticmethod
    def create_notification(
        recipient: User,
        notification_type: str,
        title: str,
        message: str,
        sender: User = None,
        related_object_id: int = None
    ) -> Notification:
        """Создать уведомление"""
        return Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            related_object_id=related_object_id
        )
    
    @staticmethod
    def notify_assignment_due(assignment: Assignment):
        """Уведомить о крайнем сроке задания"""
        enrolled_students = Enrollment.objects.filter(
            subject=assignment.lesson.theme.subject,
            status='active'
        ).values_list('student', flat=True)
        
        for student_id in enrolled_students:
            student = User.objects.get(id=student_id)
            NotificationService.create_notification(
                recipient=student,
                notification_type='assignment_due',
                title=f'Крайний срок задания: {assignment.title}',
                message=f'До крайнего срока задания "{assignment.title}" осталось меньше 24 часов.',
                related_object_id=assignment.id
            )
    
    @staticmethod
    def notify_grade_posted(grade: Grade):
        """Уведомить о выставленной оценке"""
        NotificationService.create_notification(
            recipient=grade.student,
            notification_type='grade_posted',
            title='Выставлена новая оценка',
            message=f'Вам выставлена оценка {grade.grade} по курсу "{grade.subject.name}".',
            sender=grade.grader,
            related_object_id=grade.id
        )
    
    @staticmethod
    def notify_new_forum_post(post: ForumPost):
        """Уведомить о новом посте на форуме"""
        # Уведомляем участников дискуссии
        discussion_participants = ForumPost.objects.filter(
            discussion=post.discussion
        ).values_list('author', flat=True).distinct()
        
        for participant_id in discussion_participants:
            if participant_id != post.author.id:
                participant = User.objects.get(id=participant_id)
                NotificationService.create_notification(
                    recipient=participant,
                    notification_type='new_forum_post',
                    title=f'Новый пост в дискуссии: {post.discussion.name}',
                    message=f'{post.author.get_full_name() or post.author.username} добавил новый пост.',
                    sender=post.author,
                    related_object_id=post.id
                )
    
    @staticmethod
    def notify_badge_awarded(user_badge: UserBadge):
        """Уведомить о получении значка"""
        NotificationService.create_notification(
            recipient=user_badge.user,
            notification_type='badge_awarded',
            title='Получен новый значок!',
            message=f'Поздравляем! Вы получили значок "{user_badge.badge.name}".',
            sender=user_badge.awarded_by,
            related_object_id=user_badge.id
        )


class BadgeService:
    """Сервис для автоматического присуждения значков"""
    
    @staticmethod
    def check_and_award_badges(user: User, context: str = None):
        """Проверить и присудить значки пользователю"""
        if context == 'course_completion':
            BadgeService._check_course_completion_badges(user)
        elif context == 'test_completion':
            BadgeService._check_test_badges(user)
        elif context == 'forum_participation':
            BadgeService._check_forum_badges(user)
        else:
            # Проверить все типы значков
            BadgeService._check_course_completion_badges(user)
            BadgeService._check_test_badges(user)
            BadgeService._check_forum_badges(user)
    
    @staticmethod
    def _check_course_completion_badges(user: User):
        """Проверить значки за завершение курсов"""
        completed_courses = Enrollment.objects.filter(
            student=user,
            status='completed'
        ).count()
        
        # Значок за первый завершенный курс
        if completed_courses >= 1:
            badge = Badge.objects.filter(badge_type='course_completion').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                user_badge = UserBadge.objects.create(user=user, badge=badge)
                NotificationService.notify_badge_awarded(user_badge)
    
    @staticmethod
    def _check_test_badges(user: User):
        """Проверить значки за тесты"""
        perfect_tests = TestAttempt.objects.filter(
            student=user,
            score=100,
            is_passed=True
        ).count()
        
        # Значок за идеальный результат теста
        if perfect_tests >= 1:
            badge = Badge.objects.filter(badge_type='perfect_quiz').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                user_badge = UserBadge.objects.create(user=user, badge=badge)
                NotificationService.notify_badge_awarded(user_badge)
    
    @staticmethod
    def _check_forum_badges(user: User):
        """Проверить значки за участие в форумах"""
        forum_posts = ForumPost.objects.filter(author=user).count()
        
        # Значок за активное участие в форумах
        if forum_posts >= 10:
            badge = Badge.objects.filter(badge_type='active_participant').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                user_badge = UserBadge.objects.create(user=user, badge=badge)
                NotificationService.notify_badge_awarded(user_badge)


class ProgressTrackingService:
    """Сервис для отслеживания прогресса"""
    
    @staticmethod
    def calculate_course_progress(user: User, subject: Subject) -> float:
        """Рассчитать прогресс пользователя по курсу"""
        from .models import Lesson
        
        # Получить все видимые уроки курса
        total_lessons = Lesson.objects.filter(
            theme__subject=subject,
            is_visible=True
        ).count()
        
        if total_lessons == 0:
            return 0.0
        
        # Подсчитать завершенные уроки (простая логика)
        completed_lessons = 0
        
        progress = (completed_lessons / total_lessons) * 100
        
        # Обновить прогресс в записи на курс
        enrollment = Enrollment.objects.filter(student=user, subject=subject).first()
        if enrollment:
            enrollment.progress_percentage = min(progress, 100)
            enrollment.save()
        
        return progress
    
    @staticmethod
    def update_course_completion(user: User, subject: Subject):
        """Обновить статус завершения курса"""
        progress = ProgressTrackingService.calculate_course_progress(user, subject)
        
        if progress >= 100:
            enrollment = Enrollment.objects.filter(student=user, subject=subject).first()
            if enrollment and enrollment.status != 'completed':
                enrollment.status = 'completed'
                enrollment.completion_date = timezone.now()
                enrollment.save()
                
                # Присудить значки за завершение курса
                BadgeService.check_and_award_badges(user, 'course_completion')


class ReportsService:
    """Сервис для генерации отчетов"""
    
    @staticmethod
    def generate_student_report(user: User) -> Dict[str, Any]:
        """Генерировать отчет по студенту"""
        enrollments = Enrollment.objects.filter(student=user)
        
        report = {
            'user_info': {
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                'email': user.email,
            },
            'enrollments': {
                'total': enrollments.count(),
                'active': enrollments.filter(status='active').count(),
                'completed': enrollments.filter(status='completed').count(),
            },
            'grades': {
                'total': Grade.objects.filter(student=user).count(),
                'average': Grade.objects.filter(student=user).aggregate(
                    avg=models.Avg('grade')
                )['avg'] or 0,
            },
            'tests': {
                'total_attempts': TestAttempt.objects.filter(student=user).count(),
                'passed': TestAttempt.objects.filter(
                    student=user, is_passed=True
                ).count(),
            },
            'assignments': {
                'submitted': SubmittedAssignment.objects.filter(student=user).count(),
            },
            'badges': {
                'total': UserBadge.objects.filter(user=user).count(),
            },
            'forum_activity': {
                'posts': ForumPost.objects.filter(author=user).count(),
            }
        }
        
        return report
    
    @staticmethod
    def generate_course_report(subject: Subject) -> Dict[str, Any]:
        """Генерировать отчет по курсу"""
        enrollments = Enrollment.objects.filter(subject=subject)
        
        report = {
            'course_info': {
                'id': subject.id,
                'name': subject.name,
                'teacher': subject.teacher.get_full_name() or subject.teacher.username,
                'created': subject.creationdate,
            },
            'enrollments': {
                'total': enrollments.count(),
                'active': enrollments.filter(status='active').count(),
                'completed': enrollments.filter(status='completed').count(),
                'average_progress': enrollments.aggregate(
                    avg=models.Avg('progress_percentage')
                )['avg'] or 0,
            },
            'grades': {
                'total': Grade.objects.filter(subject=subject).count(),
                'average': Grade.objects.filter(subject=subject).aggregate(
                    avg=models.Avg('grade')
                )['avg'] or 0,
            },
            'tests': {
                'total': Test.objects.filter(
                    lesson__theme__subject=subject
                ).count(),
                'attempts': TestAttempt.objects.filter(
                    test__lesson__theme__subject=subject
                ).count(),
            },
            'assignments': {
                'total': Assignment.objects.filter(
                    lesson__theme__subject=subject
                ).count(),
                'submitted': SubmittedAssignment.objects.filter(
                    assignment__lesson__theme__subject=subject
                ).count(),
            }
        }
        
        return report


class GradingService:
    """Сервис для автоматического оценивания"""
    
    @staticmethod
    def auto_grade_test(test_attempt: TestAttempt):
        """Автоматически оценить тест"""
        total_points = 0
        earned_points = 0
        
        for student_answer in test_attempt.answers.all():
            question = student_answer.question
            total_points += question.points
            
            # Проверить правильность ответа
            student_answer.check_correctness()
            
            if student_answer.is_correct:
                earned_points += question.points
        
        # Рассчитать процент
        if total_points > 0:
            score = (earned_points / total_points) * 100
        else:
            score = 0
        
        # Обновить попытку
        test_attempt.score = score
        test_attempt.is_passed = score >= test_attempt.test.passing_score
        test_attempt.completed_at = timezone.now()
        test_attempt.status = 'completed'
        test_attempt.save()
        
        # Создать запись об оценке
        Grade.objects.create(
            subject=test_attempt.test.lesson.theme.subject,
            student=test_attempt.student,
            grade=score,
            grade_type='automatic'
        )
        
        # Присудить значки
        if test_attempt.is_passed:
            BadgeService.check_and_award_badges(
                test_attempt.student, 
                'test_completion'
            )


class CalendarService:
    """Сервис для работы с календарем"""
    
    @staticmethod
    def create_assignment_deadline_event(assignment: Assignment):
        """Создать событие календаря для крайнего срока задания"""
        # Создаем событие только если у задания есть deadline
        if assignment.deadline:
            CalendarEvent.objects.create(
                subject=assignment.lesson.theme.subject,
                title=f'Крайний срок: {assignment.title}',
                description=f'Крайний срок сдачи задания "{assignment.title}"',
                event_type='deadline',
                start_date=timezone.make_aware(
                    timezone.datetime.combine(assignment.deadline, timezone.datetime.min.time())
                ),
                created_by=assignment.lesson.theme.subject.teacher
            )
    
    @staticmethod
    def create_test_availability_events(test: Test):
        """Создать события календаря для доступности теста"""
        if test.available_from:
            CalendarEvent.objects.create(
                subject=test.lesson.theme.subject,
                title=f'Тест доступен: {test.title}',
                description=f'Тест "{test.title}" становится доступным',
                event_type='quiz',
                start_date=test.available_from,
                created_by=test.lesson.theme.subject.teacher
            )
        
        if test.available_until:
            CalendarEvent.objects.create(
                subject=test.lesson.theme.subject,
                title=f'Тест закрывается: {test.title}',
                description=f'Последний день для прохождения теста "{test.title}"',
                event_type='deadline',
                start_date=test.available_until,
                created_by=test.lesson.theme.subject.teacher
            )


class EmailService:
    """Сервис для отправки email уведомлений"""
    
    @staticmethod
    def send_welcome_email(user: User):
        """Отправить приветственное письмо"""
        if hasattr(settings, 'EMAIL_HOST') and user.email:
            send_mail(
                subject='Добро пожаловать в LMS!',
                message=f'Здравствуйте, {user.get_full_name() or user.username}!\n\n'
                       'Добро пожаловать в нашу систему обучения.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
    
    @staticmethod
    def send_assignment_reminder(user: User, assignment: Assignment):
        """Отправить напоминание о задании"""
        if hasattr(settings, 'EMAIL_HOST') and user.email:
            send_mail(
                subject=f'Напоминание: {assignment.title}',
                message=f'Напоминаем о крайнем сроке задания "{assignment.title}"\n'
                       f'Дата сдачи: {assignment.deadline}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )


class IntegrationService:
    """Сервис для интеграции с внешними системами"""
    
    @staticmethod
    def sync_user_data(user: User) -> Dict[str, Any]:
        """Синхронизировать данные пользователя с внешними системами"""
        sync_result = {
            'status': 'success',
            'user_id': user.id,
            'synced_at': timezone.now(),
            'external_systems': []
        }
        
        return sync_result
    
    @staticmethod
    def export_course_data(subject: Subject, format_type: str = 'json') -> str:
        """Экспортировать данные курса"""
        course_data = {
            'course': {
                'id': subject.id,
                'name': subject.name,
                'description': subject.description,
                'created': subject.creationdate.isoformat(),
            },
            'themes': [],
            'enrollments_count': Enrollment.objects.filter(subject=subject).count(),
        }
        
        # Добавить темы и уроки
        for theme in subject.theme_set.all():
            theme_data = {
                'id': theme.id,
                'name': theme.name,
                'description': theme.description,
                'lessons': []
            }
            
            for lesson in theme.lesson_set.all():
                lesson_data = {
                    'id': lesson.id,
                    'name': lesson.name,
                    'type': lesson.lessontype,
                    'description': lesson.description,
                }
                theme_data['lessons'].append(lesson_data)
            
            course_data['themes'].append(theme_data)
        
        if format_type == 'json':
            return json.dumps(course_data, ensure_ascii=False, indent=2)
        
        return course_data 