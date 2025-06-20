from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    Student, Teacher, StudentGroup, Subject, Grade, Theme,
    Lesson, Test, TestAttempt, SubmittedAssignment, UserRole,
    UserProfile, CourseCategory, CourseFormat, Enrollment, CourseFile,
    Forum, ForumDiscussion, ForumPost, CalendarEvent,
    Badge, UserBadge, Notification, PrivateMessage,
    TestBank, Question, Answer, Assignment
)
from .serializers import (
    StudentSerializer, TeacherSerializer, StudentGroupSerializer,
    SubjectSerializer, GradeSerializer, ThemeSerializer,
    LessonSerializer, TestSerializer, TestAttemptSerializer,
    SubmittedAssignmentSerializer, UserProfileSerializer,
    CourseCategorySerializer, CourseFormatSerializer, EnrollmentSerializer,
    CourseFileSerializer, ForumSerializer, ForumDiscussionSerializer,
    ForumPostSerializer, CalendarEventSerializer, BadgeSerializer,
    UserBadgeSerializer, NotificationSerializer, PrivateMessageSerializer,
    CreateSubjectSerializer, CreateForumSerializer, CreateAssignmentSerializer,
    StudentStatsSerializer, TeacherStatsSerializer, TestBankSerializer,
    QuestionSerializer, AnswerSerializer, AssignmentSerializer,
    UserRoleSerializer
)

class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet для профилей пользователей"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get', 'patch'])
    def my_profile(self, request):
        """Получить или обновить свой профиль"""
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорий курсов"""
    queryset = CourseCategory.objects.filter(is_visible=True)
    serializer_class = CourseCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order', 'name']
    
    def destroy(self, request, *args, **kwargs):
        """Удаление категории с проверкой использования"""
        category = self.get_object()
        cascade = request.query_params.get('cascade', False)
        
        # Проверяем, есть ли курсы в этой категории
        courses_count = Subject.objects.filter(category=category).count()
        if courses_count > 0 and not cascade:
            return Response({
                'error': f'Нельзя удалить категорию, которая используется в {courses_count} курсах. Сначала переместите курсы в другую категорию.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, есть ли подкатегории
        subcategories_count = CourseCategory.objects.filter(parent=category).count()
        if subcategories_count > 0 and not cascade:
            return Response({
                'error': f'Нельзя удалить категорию, у которой есть {subcategories_count} подкатегорий. Сначала удалите или переместите подкатегории.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Каскадное удаление курсов если указан параметр cascade
        if cascade and courses_count > 0:
            Subject.objects.filter(category=category).delete()
        
        # Каскадное удаление подкатегорий если указан параметр cascade
        if cascade and subcategories_count > 0:
            CourseCategory.objects.filter(parent=category).delete()
        
        return super().destroy(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Обновление категории с перемещением курсов"""
        category = self.get_object()
        move_courses_to = request.data.get('move_courses_to')
        
        if move_courses_to is not None:
            # Перемещаем курсы в другую категорию или убираем категорию
            if move_courses_to == '':
                move_courses_to = None
            
            Subject.objects.filter(category=category).update(category=move_courses_to)
            
            # Удаляем категорию после перемещения курсов
            category.delete()
            return Response({'message': 'Категория удалена, курсы перемещены'})
        
        return super().partial_update(request, *args, **kwargs)

class CourseFormatViewSet(viewsets.ModelViewSet):
    """ViewSet для форматов курсов"""
    queryset = CourseFormat.objects.filter(is_active=True)
    serializer_class = CourseFormatSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']
    
    def destroy(self, request, *args, **kwargs):
        """Удаление формата с проверкой использования"""
        format_obj = self.get_object()
        cascade = request.query_params.get('cascade', False)
        
        # Проверяем, есть ли курсы с этим форматом
        courses_count = Subject.objects.filter(course_format=format_obj).count()
        if courses_count > 0 and not cascade:
            return Response({
                'error': f'Нельзя удалить формат, который используется в {courses_count} курсах. Сначала измените формат у этих курсов.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Каскадное удаление курсов если указан параметр cascade
        if cascade and courses_count > 0:
            Subject.objects.filter(course_format=format_obj).delete()
        
        return super().destroy(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Обновление формата с изменением у курсов"""
        format_obj = self.get_object()
        move_courses_to = request.data.get('move_courses_to')
        
        if move_courses_to is not None:
            # Изменяем формат у курсов
            try:
                new_format = CourseFormat.objects.get(id=move_courses_to)
                Subject.objects.filter(course_format=format_obj).update(course_format=new_format)
                
                # Удаляем формат после изменения у курсов
                format_obj.delete()
                return Response({'message': 'Формат удален, у курсов изменен формат'})
            except CourseFormat.DoesNotExist:
                return Response({
                    'error': 'Указанный формат для перемещения не найден'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().partial_update(request, *args, **kwargs)

class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet для курсов (предметов)"""
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_published', 'category', 'course_format']
    search_fields = ['name', 'description', 'summary']
    ordering_fields = ['creationdate', 'name', 'start_date']
    ordering = ['-creationdate']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Subject.objects.filter(teacher=user)
        else:
            # Студенты видят только опубликованные курсы
            return Subject.objects.filter(is_published=True)
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateSubjectSerializer
        return SubjectSerializer
    
    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """Записаться на курс"""
        subject = self.get_object()
        
        if subject.enrollment_key and request.data.get('enrollment_key') != subject.enrollment_key:
            return Response({'error': 'Неверный ключ записи'}, status=status.HTTP_400_BAD_REQUEST)
        
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            subject=subject,
            defaults={'status': 'active'}
        )
        
        if created:
            return Response({'message': 'Вы успешно записались на курс'})
        else:
            return Response({'message': 'Вы уже записаны на этот курс'})
    
    @action(detail=True, methods=['delete'])
    def unenroll(self, request, pk=None):
        """Отписаться от курса"""
        subject = self.get_object()
        try:
            enrollment = Enrollment.objects.get(student=request.user, subject=subject)
            enrollment.delete()
            return Response({'message': 'Вы отписались от курса'})
        except Enrollment.DoesNotExist:
            return Response({'error': 'Вы не записаны на этот курс'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def enrolled_students(self, request, pk=None):
        """Получить список записанных студентов"""
        subject = self.get_object()
        enrollments = Enrollment.objects.filter(subject=subject, status='active')
        students = [enrollment.student for enrollment in enrollments]
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)

class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet для записей на курсы"""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'subject']
    
    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

class ThemeViewSet(viewsets.ModelViewSet):
    """ViewSet для тем курсов"""
    serializer_class = ThemeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['subject', 'is_visible']
    ordering_fields = ['sort_order', 'creationdate']
    ordering = ['sort_order']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Theme.objects.filter(subject__teacher=user)
        else:
            # Студенты видят только темы курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Theme.objects.filter(subject__in=enrolled_subjects, is_visible=True)

class LessonViewSet(viewsets.ModelViewSet):
    """ViewSet для уроков"""
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['theme', 'lessontype', 'is_visible']
    ordering_fields = ['sort_order', 'creationdate']
    ordering = ['sort_order']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Lesson.objects.filter(theme__subject__teacher=user)
        else:
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Lesson.objects.filter(
                theme__subject__in=enrolled_subjects,
                is_visible=True
            )

class ForumViewSet(viewsets.ModelViewSet):
    """ViewSet для форумов"""
    serializer_class = ForumSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['subject', 'forum_type']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Forum.objects.filter(subject__teacher=user)
        else:
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Forum.objects.filter(subject__in=enrolled_subjects)
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateForumSerializer
        return ForumSerializer

class ForumDiscussionViewSet(viewsets.ModelViewSet):
    """ViewSet для дискуссий форума"""
    serializer_class = ForumDiscussionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['forum', 'is_pinned', 'is_locked']
    search_fields = ['name']
    ordering_fields = ['created_at', 'last_post_at', 'posts_count']
    ordering = ['-is_pinned', '-last_post_at']

class ForumPostViewSet(viewsets.ModelViewSet):
    """ViewSet для постов форума"""
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['discussion']
    ordering_fields = ['created_at']
    ordering = ['created_at']

class TestBankViewSet(viewsets.ModelViewSet):
    """ViewSet для банков тестов"""
    serializer_class = TestBankSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['subject']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return TestBank.objects.filter(created_by=user)
        else:
            return TestBank.objects.filter(subject__enrollment__student=user)

class TestViewSet(viewsets.ModelViewSet):
    """ViewSet для тестов"""
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['lesson', 'type', 'is_active']
    search_fields = ['name', 'title', 'description']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Test.objects.filter(lesson__theme__subject__teacher=user)
        else:
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Test.objects.filter(
                lesson__theme__subject__in=enrolled_subjects,
                is_active=True
            )
    
    @action(detail=True, methods=['post'])
    def start_attempt(self, request, pk=None):
        """Начать попытку прохождения теста"""
        test = self.get_object()
        
        # Проверить количество попыток
        attempts_count = TestAttempt.objects.filter(
            test=test, student=request.user
        ).count()
        
        if attempts_count >= test.max_attempts:
            return Response(
                {'error': 'Превышено максимальное количество попыток'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создать новую попытку
        attempt = TestAttempt.objects.create(
            test=test,
            student=request.user,
            attempt_number=attempts_count + 1
        )
        
        serializer = TestAttemptSerializer(attempt)
        return Response(serializer.data)

class TestAttemptViewSet(viewsets.ModelViewSet):
    """ViewSet для попыток прохождения тестов"""
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TestAttempt.objects.filter(student=self.request.user)

class AssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet для заданий"""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lesson']
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'creationdate']
    ordering = ['deadline']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Assignment.objects.filter(lesson__theme__subject__teacher=user)
        else:
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Assignment.objects.filter(
                lesson__theme__subject__in=enrolled_subjects
            )
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateAssignmentSerializer
        return AssignmentSerializer

class SubmittedAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet для сданных заданий"""
    serializer_class = SubmittedAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['assignment', 'grade']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Преподаватели видят все сданные задания по своим курсам
            return SubmittedAssignment.objects.filter(
                assignment__lesson__theme__subject__teacher=user
            )
        else:
            return SubmittedAssignment.objects.filter(student=user)

class CalendarEventViewSet(viewsets.ModelViewSet):
    """ViewSet для событий календаря"""
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['subject', 'event_type']
    ordering_fields = ['start_date']
    ordering = ['start_date']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return CalendarEvent.objects.filter(subject__teacher=user)
        else:
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return CalendarEvent.objects.filter(subject__in=enrolled_subjects)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Получить предстоящие события"""
        queryset = self.get_queryset().filter(
            start_date__gte=timezone.now(),
            start_date__lte=timezone.now() + timedelta(days=7)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class BadgeViewSet(viewsets.ModelViewSet):
    """ViewSet для значков"""
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['badge_type', 'subject', 'is_active']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        return Badge.objects.filter(is_active=True)

class UserBadgeViewSet(viewsets.ModelViewSet):
    """ViewSet для полученных значков"""
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet для уведомлений"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'notification_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Отметить уведомление как прочитанное"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Уведомление отмечено как прочитанное'})
    
    @action(detail=False, methods=['patch'])
    def mark_all_as_read(self, request):
        """Отметить все уведомления как прочитанные"""
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({'message': 'Все уведомления отмечены как прочитанные'})

class PrivateMessageViewSet(viewsets.ModelViewSet):
    """ViewSet для личных сообщений"""
    serializer_class = PrivateMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_read']
    search_fields = ['subject', 'content']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
)

class AnalyticsViewSet(viewsets.ViewSet):
    """ViewSet для аналитики"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def student_stats(self, request):
        """Статистика студента"""
        user = request.user
        
        # Оценки
        grades = Grade.objects.filter(student=user)
        average_grade = grades.aggregate(Avg('grade'))['grade__avg'] or 0
        
        # Тесты
        total_tests = TestAttempt.objects.filter(student=user).count()
        passed_tests = TestAttempt.objects.filter(
            student=user, is_passed=True
        ).count()
        
        # Задания
        submitted_assignments = SubmittedAssignment.objects.filter(
            student=user
        ).count()
        
        # Курсы
        enrolled_courses = Enrollment.objects.filter(
            student=user, status='active'
        ).count()
        completed_courses = Enrollment.objects.filter(
            student=user, status='completed'
        ).count()
        
        # Значки
        total_badges = UserBadge.objects.filter(user=user).count()
        
        # Посты на форуме
        forum_posts = ForumPost.objects.filter(author=user).count()
        
        stats = {
            'average_grade': round(average_grade, 2),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'submitted_assignments': submitted_assignments,
            'enrolled_courses': enrolled_courses,
            'completed_courses': completed_courses,
            'total_badges': total_badges,
            'forum_posts': forum_posts
        }
        
        serializer = StudentStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def teacher_stats(self, request):
        """Статистика преподавателя"""
        user = request.user
        
        if not hasattr(user, 'teacher'):
            return Response(
                {'error': 'Пользователь не является преподавателем'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Курсы преподавателя
        subjects = Subject.objects.filter(teacher=user)
        
        # Студенты
        total_students = Enrollment.objects.filter(
            subject__in=subjects, status='active'
        ).values('student').distinct().count()
        
        # Средние оценки
        average_grades = Grade.objects.filter(
            subject__in=subjects
        ).aggregate(Avg('grade'))['grade__avg'] or 0
        
        # Активные тесты
        active_tests = Test.objects.filter(
            lesson__theme__subject__in=subjects,
            is_active=True
        ).count()
        
        # Задания, ожидающие проверки
        pending_assignments = SubmittedAssignment.objects.filter(
            assignment__lesson__theme__subject__in=subjects,
            grade=0
        ).count()
        
        # Дискуссии форума
        forum_discussions = ForumDiscussion.objects.filter(
            forum__subject__in=subjects
        ).count()
        
        # Выданные значки
        badges_awarded = UserBadge.objects.filter(
            badge__subject__in=subjects
        ).count()
        
        stats = {
            'total_students': total_students,
            'total_subjects': subjects.count(),
            'average_grades': round(average_grades, 2),
            'active_tests': active_tests,
            'pending_assignments': pending_assignments,
            'forum_discussions': forum_discussions,
            'badges_awarded': badges_awarded
        }
        
        serializer = TeacherStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Общая информация для дашборда"""
        user = request.user
        
        # Предстоящие события
        upcoming_events = CalendarEvent.objects.filter(
            subject__enrollment__student=user,
            start_date__gte=timezone.now(),
            start_date__lte=timezone.now() + timedelta(days=7)
        )[:5]
        
        # Непрочитанные уведомления
        unread_notifications = Notification.objects.filter(
            recipient=user, is_read=False
            ).count()
        
        # Последние оценки
        recent_grades = Grade.objects.filter(
            student=user
        ).order_by('-lastupdate')[:5]
        
        # Активные задания
        active_assignments = Assignment.objects.filter(
            lesson__theme__subject__enrollment__student=user,
            deadline__gte=timezone.now()
        ).order_by('deadline')[:5]
        
        dashboard_data = {
            'upcoming_events': CalendarEventSerializer(upcoming_events, many=True).data,
            'unread_notifications': unread_notifications,
            'recent_grades': GradeSerializer(recent_grades, many=True).data,
            'active_assignments': AssignmentSerializer(active_assignments, many=True).data
        }
        
        return Response(dashboard_data)

class UserRoleViewSet(viewsets.ModelViewSet):
    """ViewSet для ролей пользователей"""
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRole.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Получить текущие роли пользователя"""
        roles = UserRole.objects.filter(user=request.user, is_active=True)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def switch_role(self, request):
        """Переключить роль пользователя (только для демо)"""
        role_name = request.data.get('role')
        
        if role_name not in ['student', 'teacher', 'admin']:
            return Response(
                {'error': 'Недопустимая роль'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Деактивируем все роли
        UserRole.objects.filter(user=request.user).update(is_active=False)
        
        # Создаем или активируем новую роль
        role, created = UserRole.objects.get_or_create(
            user=request.user,
            role=role_name,
            defaults={'is_active': True}
        )
        
        if not created:
            role.is_active = True
            role.save()
        
        return Response({
            'message': f'Роль переключена на {role_name}',
            'role': role_name
        })
