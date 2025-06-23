from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from .base_views import (
    BaseLMSViewSet, UserOwnedViewSet, SubjectRelatedViewSet, 
    ReadOnlyLMSViewSet, ToggleVisibilityMixin, OrderingMixin
)
from .utils import get_user_accessible_subjects, get_upcoming_deadlines
from .analytics import AnalyticsService
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
    CreateSubjectSerializer, UpdateSubjectSerializer, CreateForumSerializer, CreateAssignmentSerializer,
    StudentStatsSerializer, TeacherStatsSerializer, TestBankSerializer,
    QuestionSerializer, AnswerSerializer, AssignmentSerializer,
    UserRoleSerializer, CreateLessonSerializer, UpdateLessonSerializer,
    CreateThemeSerializer, UpdateThemeSerializer
)

class UserProfileViewSet(UserOwnedViewSet):
    """ViewSet для профилей пользователей"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    
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

class CourseCategoryViewSet(ReadOnlyLMSViewSet):
    """ViewSet для категорий курсов"""
    queryset = CourseCategory.objects.filter(is_visible=True)
    serializer_class = CourseCategorySerializer
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

class CourseFormatViewSet(ReadOnlyLMSViewSet):
    """ViewSet для форматов курсов"""
    queryset = CourseFormat.objects.filter(is_active=True)
    serializer_class = CourseFormatSerializer
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

class SubjectViewSet(BaseLMSViewSet):
    """ViewSet для курсов (предметов)"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filterset_fields = ['is_published', 'category', 'course_format']
    search_fields = ['name', 'description', 'summary']
    ordering_fields = ['creationdate', 'name', 'start_date']
    ordering = ['-creationdate']
    
    def get_queryset(self):
        return get_user_accessible_subjects(self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSubjectSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateSubjectSerializer
        return SubjectSerializer
    
    def perform_update(self, serializer):
        """Обновление курса с проверкой прав"""
        subject = self.get_object()
        user = self.request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        # Проверяем права на редактирование
        if 'admin' not in user_roles and subject.teacher != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("У вас нет прав на редактирование этого курса")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Удаление курса с проверкой прав"""
        user = self.request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        # Проверяем права на удаление
        if 'admin' not in user_roles and instance.teacher != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("У вас нет прав на удаление этого курса")
        
        instance.delete()
    
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
        serializer = LMSUserSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Дублирование курса со всем содержимым"""
        course = self.get_object()
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        if 'admin' not in user_roles and course.teacher != user:
            return Response({'error': 'У вас нет прав для дублирования этого курса'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Создаем копию курса
        new_course_data = {
            'name': f"{course.name} (копия)",
            'description': course.description,
            'summary': course.summary,
            'category': course.category.id if course.category else None,
            'course_format': course.course_format.id if course.course_format else None,
            'is_published': False,  # Копии создаются как черновики
            'is_self_enrollment': course.is_self_enrollment,
            'completion_tracking': course.completion_tracking,
            'guest_access': course.guest_access,
        }
        
        serializer = CreateSubjectSerializer(data=new_course_data)
        if serializer.is_valid():
            new_course = serializer.save(teacher=user)
            
            # Копируем темы и уроки
            themes = Theme.objects.filter(subject=course).order_by('sort_order')
            for theme in themes:
                new_theme = Theme.objects.create(
                    name=theme.name,
                    description=theme.description,
                    subject=new_course,
                    sort_order=theme.sort_order,
                    is_visible=theme.is_visible,
                    completion_required=theme.completion_required
                )
                
                # Копируем уроки темы
                lessons = Lesson.objects.filter(theme=theme).order_by('sort_order')
                for lesson in lessons:
                    Lesson.objects.create(
                        name=lesson.name,
                        description=lesson.description,
                        lessontype=lesson.lessontype,
                        content=lesson.content,
                        theme=new_theme,
                        availability_start=lesson.availability_start,
                        availability_end=lesson.availability_end,
                        completion_required=lesson.completion_required,
                        sort_order=lesson.sort_order,
                        is_visible=lesson.is_visible
                    )
            
            return Response(SubjectSerializer(new_course).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def toggle_published(self, request, pk=None):
        """Переключение статуса публикации курса"""
        course = self.get_object()
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        if 'admin' not in user_roles and course.teacher != user:
            return Response({'error': 'У вас нет прав для изменения статуса публикации этого курса'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        course.is_published = not course.is_published
        course.save()
        
        return Response({
            'message': f'Курс {"опубликован" if course.is_published else "снят с публикации"}',
            'is_published': course.is_published
        })
    
    @action(detail=True, methods=['get'])
    def structure(self, request, pk=None):
        """Получение полной структуры курса с темами и уроками"""
        course = self.get_object()
        
        # Проверяем доступ к курсу
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles:
            if hasattr(user, 'teacher') and course.teacher == user:
                # Преподаватель может видеть полную структуру своего курса
                pass
            elif course.is_published:
                # Для опубликованных курсов проверяем запись
                if not Enrollment.objects.filter(student=user, subject=course, status='active').exists():
                    return Response({'error': 'У вас нет доступа к этому курсу'}, 
                                  status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': 'У вас нет доступа к этому курсу'}, 
                              status=status.HTTP_403_FORBIDDEN)
        
        # Получаем темы курса
        themes = Theme.objects.filter(subject=course).order_by('sort_order')
        
        # Фильтруем по видимости для студентов
        if 'admin' not in user_roles and (not hasattr(user, 'teacher') or course.teacher != user):
            themes = themes.filter(is_visible=True)
        
        structure = []
        for theme in themes:
            lessons = Lesson.objects.filter(theme=theme).order_by('sort_order')
            
            # Фильтруем уроки по видимости для студентов
            if 'admin' not in user_roles and (not hasattr(user, 'teacher') or course.teacher != user):
                lessons = lessons.filter(is_visible=True)
            
            theme_data = ThemeSerializer(theme).data
            theme_data['lessons'] = LessonSerializer(lessons, many=True).data
            structure.append(theme_data)
        
        return Response({
            'course': SubjectSerializer(course).data,
            'structure': structure
        })

class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet для записей на курсы"""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'subject']
    
    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

class ThemeViewSet(SubjectRelatedViewSet, ToggleVisibilityMixin, OrderingMixin):
    """ViewSet для тем курсов"""
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer
    filterset_fields = ['subject', 'is_visible']
    ordering_fields = ['sort_order', 'creationdate']
    ordering = ['sort_order']
    
    def get_queryset(self):
        # Переопределяем для тем, так как нужна проверка записи студентов
        user = self.request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return self.queryset.all()
        elif 'teacher' in user_roles or hasattr(user, 'teacher'):
            return self.queryset.filter(
                Q(subject__teacher=user) | Q(subject__is_published=True)
            ).distinct()
        else:
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return self.queryset.filter(subject__in=enrolled_subjects, is_visible=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateThemeSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateThemeSerializer
        return ThemeSerializer
    
    @action(detail=True, methods=['post'])
    def reorder_lessons(self, request, pk=None):
        """Изменение порядка уроков в теме"""
        theme = self.get_object()
        lesson_ids = request.data.get('lesson_ids', [])
        
        if not lesson_ids:
            return Response({'error': 'Список ID уроков не может быть пустым'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        if 'admin' not in user_roles and theme.subject.teacher != user:
            return Response({'error': 'У вас нет прав для изменения порядка уроков'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Обновляем порядок
        for index, lesson_id in enumerate(lesson_ids):
            try:
                lesson = Lesson.objects.get(id=lesson_id, theme=theme)
                lesson.sort_order = index + 1
                lesson.save()
            except Lesson.DoesNotExist:
                return Response({'error': f'Урок с ID {lesson_id} не найден в этой теме'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Порядок уроков обновлен'}, status=status.HTTP_200_OK)

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
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return Lesson.objects.all()
        elif 'teacher' in user_roles or hasattr(user, 'teacher'):
            # Преподаватели видят уроки своих курсов + уроки опубликованных курсов
            return Lesson.objects.filter(
                Q(theme__subject__teacher=user) | Q(theme__subject__is_published=True)
            ).distinct()
        else:
            # Студенты видят только видимые уроки курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Lesson.objects.filter(
                theme__subject__in=enrolled_subjects,
                is_visible=True
            )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateLessonSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateLessonSerializer
        return LessonSerializer
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Дублирование урока"""
        lesson = self.get_object()
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        if 'admin' not in user_roles and lesson.theme.subject.teacher != user:
            return Response({'error': 'У вас нет прав для дублирования этого урока'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Создаем копию урока
        new_lesson_data = {
            'name': f"{lesson.name} (копия)",
            'description': lesson.description,
            'lessontype': lesson.lessontype,
            'content': lesson.content,
            'theme': lesson.theme.id,
            'availability_start': lesson.availability_start,
            'availability_end': lesson.availability_end,
            'completion_required': lesson.completion_required,
            'is_visible': lesson.is_visible,
        }
        
        serializer = CreateLessonSerializer(data=new_lesson_data)
        if serializer.is_valid():
            new_lesson = serializer.save()
            return Response(LessonSerializer(new_lesson).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def toggle_visibility(self, request, pk=None):
        """Переключение видимости урока"""
        lesson = self.get_object()
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        if 'admin' not in user_roles and lesson.theme.subject.teacher != user:
            return Response({'error': 'У вас нет прав для изменения видимости этого урока'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        lesson.is_visible = not lesson.is_visible
        lesson.save()
        
        return Response({
            'message': f'Урок {"показан" if lesson.is_visible else "скрыт"}',
            'is_visible': lesson.is_visible
        })
    
    @action(detail=False, methods=['get'])
    def by_course(self, request):
        """Получение уроков по курсу"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response({'error': 'course_id параметр обязателен'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = Subject.objects.get(id=course_id)
        except Subject.DoesNotExist:
            return Response({'error': 'Курс не найден'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем доступ к курсу
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles:
            if hasattr(user, 'teacher') and course.teacher == user:
                # Преподаватель может видеть все уроки своего курса
                pass
            elif course.is_published:
                # Для опубликованных курсов проверяем запись
                if not Enrollment.objects.filter(student=user, subject=course, status='active').exists():
                    return Response({'error': 'У вас нет доступа к этому курсу'}, 
                                  status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': 'У вас нет доступа к этому курсу'}, 
                              status=status.HTTP_403_FORBIDDEN)
        
        # Получаем уроки курса
        themes = Theme.objects.filter(subject=course).order_by('sort_order')
        lessons = Lesson.objects.filter(theme__in=themes).order_by('theme__sort_order', 'sort_order')
        
        # Фильтруем по видимости для студентов
        if 'admin' not in user_roles and (not hasattr(user, 'teacher') or course.teacher != user):
            lessons = lessons.filter(is_visible=True)
        
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

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

class NotificationViewSet(BaseLMSViewSet):
    """ViewSet для уведомлений"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filterset_fields = ['is_read', 'notification_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)
    
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
        stats = AnalyticsService.get_student_stats(request.user)
        serializer = StudentStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def teacher_stats(self, request):
        """Статистика преподавателя"""
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'teacher' not in user_roles and 'admin' not in user_roles:
            return Response(
                {'error': 'Пользователь не является преподавателем'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = AnalyticsService.get_teacher_stats(user)
        serializer = TeacherStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Общая информация для дашборда"""
        user = request.user
        
        # Используем утилиту для получения дедлайнов
        deadlines = get_upcoming_deadlines(user)
        
        # Непрочитанные уведомления
        unread_notifications = Notification.objects.filter(
            recipient=user, is_read=False
        ).count()
        
        # Последние оценки
        recent_grades = Grade.objects.filter(
            student=user
        ).order_by('-lastupdate')[:5]
        
        dashboard_data = {
            'upcoming_assignments': AssignmentSerializer(deadlines['assignments'], many=True).data,
            'upcoming_events': CalendarEventSerializer(deadlines['events'], many=True).data,
            'unread_notifications': unread_notifications,
            'recent_grades': GradeSerializer(recent_grades, many=True).data
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
