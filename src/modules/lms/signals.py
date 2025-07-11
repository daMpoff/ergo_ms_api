from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db import models

from .models import (
    Grade, TestAttempt, SubmittedAssignment, Assignment,
    ForumPost, Enrollment, UserProfile, CalendarEvent,
    Test, UserBadge, LessonItem, Resource
)
from .services import (
    NotificationService, BadgeService, ProgressTrackingService,
    CalendarService, EmailService, GradingService
)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создать профиль пользователя при создании нового пользователя"""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        # Отправить приветственное письмо
        EmailService.send_welcome_email(instance)


@receiver(post_save, sender=Grade)
def notify_grade_posted(sender, instance, created, **kwargs):
    """Уведомить студента о выставленной оценке"""
    if created:
        NotificationService.notify_grade_posted(instance)
        
        # Проверить и присудить значки
        BadgeService.check_and_award_badges(instance.student)
        
        # Обновить прогресс по курсу
        ProgressTrackingService.update_course_completion(
            instance.student, 
            instance.subject
        )


@receiver(post_save, sender=TestAttempt)
def process_test_completion(sender, instance, created, **kwargs):
    """Обработать завершение теста"""
    if not created and instance.status == 'completed':
        # Автоматически оценить тест, если он не был оценен
        if instance.score is None:
            GradingService.auto_grade_test(instance)
        
        # Проверить и присудить значки
        if instance.is_passed:
            BadgeService.check_and_award_badges(instance.student, 'test_completion')


@receiver(post_save, sender=SubmittedAssignment)
def process_assignment_submission(sender, instance, created, **kwargs):
    """Обработать сдачу задания"""
    if created:
        # Уведомить преподавателя о новой сдаче
        teacher = instance.assignment.lesson.theme.subject.teacher
        NotificationService.create_notification(
            recipient=teacher,
            notification_type='assignment_submission',
            title=f'Новая сдача задания: {instance.assignment.title}',
            message=f'Студент {instance.student.get_full_name() or instance.student.username} '
                   f'сдал задание "{instance.assignment.title}".',
            sender=instance.student,
            related_object_id=instance.id
        )
    
    elif not created and instance.grade > 0 and 'grade' in kwargs.get('update_fields', []):
        # Уведомить студента об оценке за задание
        NotificationService.create_notification(
            recipient=instance.student,
            notification_type='assignment_graded',
            title=f'Задание проверено: {instance.assignment.title}',
            message=f'Ваше задание "{instance.assignment.title}" проверено. '
                   f'Оценка: {instance.grade}',
            sender=instance.graded_by,
            related_object_id=instance.id
        )


@receiver(post_save, sender=Assignment)
def create_assignment_calendar_event(sender, instance, created, **kwargs):
    """Создать событие календаря для нового задания"""
    if created:
        CalendarService.create_assignment_deadline_event(instance)
        
        # Запланировать напоминания за 24 часа до крайнего срока
        # (Здесь можно использовать Celery для отложенных задач)
        pass


@receiver(post_save, sender=Test)
def create_test_calendar_events(sender, instance, created, **kwargs):
    """Создать события календаря для теста"""
    if created and (instance.available_from or instance.available_until):
        CalendarService.create_test_availability_events(instance)


@receiver(post_save, sender=ForumPost)
def process_forum_post(sender, instance, created, **kwargs):
    """Обработать новый пост на форуме"""
    if created:
        # Уведомить участников дискуссии
        NotificationService.notify_new_forum_post(instance)
        
        # Обновить количество постов в дискуссии
        discussion = instance.discussion
        discussion.posts_count = discussion.posts.count()
        discussion.last_post_at = instance.created_at
        discussion.save()
        
        # Проверить значки за участие в форумах
        BadgeService.check_and_award_badges(instance.author, 'forum_participation')


@receiver(post_save, sender=Enrollment)
def process_enrollment(sender, instance, created, **kwargs):
    """Обработать запись на курс"""
    if created:
        # Уведомить студента о записи на курс
        NotificationService.create_notification(
            recipient=instance.student,
            notification_type='enrollment_confirmed',
            title=f'Запись на курс: {instance.subject.name}',
            message=f'Вы успешно записались на курс "{instance.subject.name}".',
            related_object_id=instance.id
        )
        
        # Уведомить преподавателя о новом студенте
        NotificationService.create_notification(
            recipient=instance.subject.teacher,
            notification_type='new_enrollment',
            title=f'Новый студент на курсе: {instance.subject.name}',
            message=f'Студент {instance.student.get_full_name() or instance.student.username} '
                   f'записался на ваш курс "{instance.subject.name}".',
            sender=instance.student,
            related_object_id=instance.id
        )
    
    elif not created and instance.status == 'completed' and 'status' in kwargs.get('update_fields', []):
        # Курс завершен
        NotificationService.create_notification(
            recipient=instance.student,
            notification_type='course_completed',
            title=f'Курс завершен: {instance.subject.name}',
            message=f'Поздравляем! Вы успешно завершили курс "{instance.subject.name}".',
            related_object_id=instance.id
        )
        
        # Проверить и присудить значки за завершение курса
        BadgeService.check_and_award_badges(instance.student, 'course_completion')


@receiver(post_save, sender=UserBadge)
def notify_badge_awarded(sender, instance, created, **kwargs):
    """Уведомить о присуждении значка"""
    if created:
        NotificationService.notify_badge_awarded(instance)


# Сигналы для очистки данных
@receiver(post_delete, sender=ForumPost)
def update_discussion_stats_on_delete(sender, instance, **kwargs):
    """Обновить статистику дискуссии при удалении поста"""
    discussion = instance.discussion
    discussion.posts_count = discussion.posts.count()
    
    # Найти последний пост для обновления времени
    last_post = discussion.posts.order_by('-created_at').first()
    if last_post:
        discussion.last_post_at = last_post.created_at
    else:
        discussion.last_post_at = discussion.created_at
    
    discussion.save()


# Сигналы для валидации и предварительной обработки
@receiver(pre_save, sender=TestAttempt)
def validate_test_attempt(sender, instance, **kwargs):
    """Валидировать попытку прохождения теста"""
    if instance.pk is None:  # Новая попытка
        # Проверить максимальное количество попыток
        existing_attempts = TestAttempt.objects.filter(
            test=instance.test,
            student=instance.student
        ).count()
        
        if existing_attempts >= instance.test.max_attempts:
            raise ValueError(f'Превышено максимальное количество попыток ({instance.test.max_attempts})')
        
        # Проверить доступность теста по времени
        now = timezone.now()
        if instance.test.available_from and now < instance.test.available_from:
            raise ValueError('Тест еще не доступен')
        
        if instance.test.available_until and now > instance.test.available_until:
            raise ValueError('Время для прохождения теста истекло')


@receiver(pre_save, sender=SubmittedAssignment)
def validate_assignment_submission(sender, instance, **kwargs):
    """Валидировать сдачу задания"""
    if instance.pk is None:  # Новая сдача
        # Проверить крайний срок, если он установлен
        if (instance.assignment.deadline and 
            not instance.assignment.allow_late_submissions and 
            timezone.now().date() > instance.assignment.deadline):
            raise ValueError('Крайний срок сдачи задания истек')


# Периодические задачи (здесь показаны как функции, в реальности можно использовать Celery)
def send_assignment_reminders():
    """Отправить напоминания о заданиях (должно вызываться периодически)"""
    tomorrow = timezone.now().date() + timedelta(days=1)
    
    # Найти задания с крайним сроком завтра (исключаем задания без deadline)
    assignments_due_tomorrow = Assignment.objects.filter(
        deadline=tomorrow
    ).exclude(deadline__isnull=True)
    
    for assignment in assignments_due_tomorrow:
        # Найти студентов, которые еще не сдали задание
        enrolled_students = Enrollment.objects.filter(
            subject=assignment.lesson.theme.subject,
            status='active'
        ).values_list('student', flat=True)
        
        submitted_students = SubmittedAssignment.objects.filter(
            assignment=assignment
        ).values_list('student', flat=True)
        
        students_to_remind = set(enrolled_students) - set(submitted_students)
        
        for student_id in students_to_remind:
            student = User.objects.get(id=student_id)
            NotificationService.create_notification(
                recipient=student,
                notification_type='assignment_due',
                title=f'Напоминание: {assignment.title}',
                message=f'Завтра истекает срок сдачи задания "{assignment.title}".',
                related_object_id=assignment.id
            )
            
            # Отправить email напоминание
            EmailService.send_assignment_reminder(student, assignment)


def cleanup_old_notifications():
    """Очистить старые уведомления (должно вызываться периодически)"""
    # Удалить прочитанные уведомления старше 30 дней
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_notifications = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff_date
    )
    
    deleted_count = old_notifications.count()
    old_notifications.delete()
    
    return deleted_count


def update_course_progress_for_all():
    """Обновить прогресс для всех активных записей на курсы"""
    active_enrollments = Enrollment.objects.filter(status='active')
    
    for enrollment in active_enrollments:
        ProgressTrackingService.calculate_course_progress(
            enrollment.student,
            enrollment.subject
        )


# Сигналы для автоматического управления LessonItem
@receiver(post_save, sender=Test)
def create_lesson_item_for_test(sender, instance, created, **kwargs):
    """Создает LessonItem при создании теста для урока"""
    if created and instance.lesson:
        # Получаем максимальный sort_order для этого урока
        max_order = LessonItem.objects.filter(lesson=instance.lesson).aggregate(
            max_order=models.Max('sort_order')
        )['max_order']
        
        LessonItem.objects.create(
            lesson=instance.lesson,
            item_type='test',
            test=instance,
            sort_order=(max_order or 0) + 1
        )

@receiver(post_save, sender=Assignment)
def create_lesson_item_for_assignment(sender, instance, created, **kwargs):
    """Создает LessonItem при создании задания для урока"""
    if created and instance.lesson:
        # Получаем максимальный sort_order для этого урока
        max_order = LessonItem.objects.filter(lesson=instance.lesson).aggregate(
            max_order=models.Max('sort_order')
        )['max_order']
        
        LessonItem.objects.create(
            lesson=instance.lesson,
            item_type='assignment',
            assignment=instance,
            sort_order=(max_order or 0) + 1
        )

@receiver(post_save, sender=Resource)
def create_lesson_item_for_resource(sender, instance, created, **kwargs):
    """Создает LessonItem при создании ресурса для урока"""
    if created and instance.lesson:
        # Получаем максимальный sort_order для этого урока
        max_order = LessonItem.objects.filter(lesson=instance.lesson).aggregate(
            max_order=models.Max('sort_order')
        )['max_order']
        
        LessonItem.objects.create(
            lesson=instance.lesson,
            item_type='resource',
            resource=instance,
            sort_order=(max_order or 0) + 1
        )

@receiver(post_delete, sender=Test)
def delete_lesson_item_for_test(sender, instance, **kwargs):
    """Удаляет связанные LessonItem при удалении теста"""
    LessonItem.objects.filter(test=instance).delete()

@receiver(post_delete, sender=Assignment)
def delete_lesson_item_for_assignment(sender, instance, **kwargs):
    """Удаляет связанные LessonItem при удалении задания"""
    LessonItem.objects.filter(assignment=instance).delete()

@receiver(post_delete, sender=Resource)
def delete_lesson_item_for_resource(sender, instance, **kwargs):
    """Удаляет связанные LessonItem при удалении ресурса"""
    LessonItem.objects.filter(resource=instance).delete()

# Сигнал для обновления LessonItem при изменении связи с уроком
@receiver(post_save, sender=Test)
def update_lesson_item_for_test(sender, instance, created, **kwargs):
    """Обновляет LessonItem при изменении связи теста с уроком"""
    if not created:
        # Удаляем старые связи
        LessonItem.objects.filter(test=instance).delete()
        
        # Создаем новую связь, если тест привязан к уроку
        if instance.lesson:
            max_order = LessonItem.objects.filter(lesson=instance.lesson).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            
            LessonItem.objects.create(
                lesson=instance.lesson,
                item_type='test',
                test=instance,
                sort_order=(max_order or 0) + 1
            )

@receiver(post_save, sender=Assignment)
def update_lesson_item_for_assignment(sender, instance, created, **kwargs):
    """Обновляет LessonItem при изменении связи задания с уроком"""
    if not created:
        # Удаляем старые связи
        LessonItem.objects.filter(assignment=instance).delete()
        
        # Создаем новую связь, если задание привязано к уроку
        if instance.lesson:
            max_order = LessonItem.objects.filter(lesson=instance.lesson).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            
            LessonItem.objects.create(
                lesson=instance.lesson,
                item_type='assignment',
                assignment=instance,
                sort_order=(max_order or 0) + 1
            )

@receiver(post_save, sender=Resource)
def update_lesson_item_for_resource(sender, instance, created, **kwargs):
    """Обновляет LessonItem при изменении связи ресурса с уроком"""
    if not created:
        # Удаляем старые связи
        LessonItem.objects.filter(resource=instance).delete()
        
        # Создаем новую связь, если ресурс привязан к уроку
        if instance.lesson:
            max_order = LessonItem.objects.filter(lesson=instance.lesson).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            
            LessonItem.objects.create(
                lesson=instance.lesson,
                item_type='resource',
                resource=instance,
                sort_order=(max_order or 0) + 1
            ) 