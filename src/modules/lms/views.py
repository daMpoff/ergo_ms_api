from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from django.db import models
from src.core.utils.mixins import SwaggerSafeMixin

from .base_views import (
    BaseLMSViewSet, UserOwnedViewSet, SubjectRelatedViewSet, 
    ReadOnlyLMSViewSet, ToggleVisibilityMixin, OrderingMixin
)
from .utils import get_user_accessible_subjects, get_upcoming_deadlines
from .analytics import AnalyticsService
from .models import (
    Student, Teacher, StudentGroup, Subject, Grade, Theme,
    Lesson, Test, TestAttempt, SubmittedAssignment, UserRole,
    UserProfile, CourseCategory, CourseFormat, Enrollment, CourseFile, Resource,
    Forum, ForumDiscussion, ForumPost, CalendarEvent,
    Badge, UserBadge, Notification, PrivateMessage,
    TestBank, Question, Answer, Assignment, LessonItem
)
from .serializers import (
    StudentSerializer, TeacherSerializer, StudentGroupSerializer,
    SubjectSerializer, GradeSerializer, ThemeSerializer,
    LessonSerializer, TestSerializer, TestAttemptSerializer,
    SubmittedAssignmentSerializer, CreateSubmittedAssignmentSerializer, LMSUserProfileSerializer,
    CourseCategorySerializer, CourseFormatSerializer, EnrollmentSerializer, CreateEnrollmentSerializer,
    CourseFileSerializer, ResourceSerializer, CreateResourceSerializer, UpdateResourceSerializer,
    ForumSerializer, ForumDiscussionSerializer,
    ForumPostSerializer, CalendarEventSerializer, BadgeSerializer,
    UserBadgeSerializer, NotificationSerializer, PrivateMessageSerializer,
    CreateSubjectSerializer, UpdateSubjectSerializer, CreateForumSerializer, CreateAssignmentSerializer,
    StudentStatsSerializer, TeacherStatsSerializer, TestBankSerializer,
    QuestionSerializer, AnswerSerializer, AssignmentSerializer,
    UserRoleSerializer, CreateLessonSerializer, UpdateLessonSerializer,
    CreateThemeSerializer, UpdateThemeSerializer, CreateTestSerializer, UpdateTestSerializer,
    CreateQuestionSerializer, CreateAnswerSerializer, LessonItemSerializer, LessonItemReorderSerializer
)

class UserProfileViewSet(SwaggerSafeMixin, UserOwnedViewSet):
    """ViewSet для профилей пользователей"""
    queryset = UserProfile.objects.all()
    serializer_class = LMSUserProfileSerializer
    
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

    def get_queryset(self):
        if self.is_swagger_fake_view():
            return UserProfile.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return UserProfile.objects.none()
        
        # Возвращаем профиль пользователя
        return UserProfile.objects.filter(user=user)

class CourseCategoryViewSet(SwaggerSafeMixin, BaseLMSViewSet):
    """ViewSet для категорий курсов"""
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer
    search_fields = ['name', 'description']
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order', 'name']
    
    def destroy(self, request, *args, **kwargs):
        """Удаление категории с каскадным удалением связанных курсов"""
        category = self.get_object()
        force_delete = request.query_params.get('force', 'false').lower() == 'true'
        
        # Считаем количество связанных объектов
        courses_count = Subject.objects.filter(category=category).count()
        subcategories_count = CourseCategory.objects.filter(parent=category).count()
        
        # Если это не принудительное удаление, возвращаем информацию для подтверждения
        if not force_delete and (courses_count > 0 or subcategories_count > 0):
            return Response({
                'requires_confirmation': True,
                'courses_count': courses_count,
                'subcategories_count': subcategories_count,
                'message': f'Удаление категории приведет к удалению {courses_count} курсов и {subcategories_count} подкатегорий. Продолжить?'
            }, status=status.HTTP_200_OK)
        
        # Принудительное удаление - удаляем все связанные объекты
        if force_delete:
            # Удаляем связанные курсы
            Subject.objects.filter(category=category).delete()
            # Удаляем подкатегории
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

    def get_queryset(self):
        if self.is_swagger_fake_view():
            return CourseCategory.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return CourseCategory.objects.none()
        
        # Проверяем роли пользователя
        user_roles = user.roles.values_list('role', flat=True)
        
        # Администраторы и преподаватели видят все категории
        if 'admin' in user_roles or 'teacher' in user_roles:
            return CourseCategory.objects.all()
        
        # Студенты видят только категории опубликованных курсов
        return CourseCategory.objects.filter(
            subjects__is_published=True
        ).distinct()

class CourseFormatViewSet(SwaggerSafeMixin, BaseLMSViewSet):
    """ViewSet для форматов курсов"""
    queryset = CourseFormat.objects.all()
    serializer_class = CourseFormatSerializer
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']
    
    def destroy(self, request, *args, **kwargs):
        """Удаление формата с каскадным удалением связанных курсов"""
        format_obj = self.get_object()
        force_delete = request.query_params.get('force', 'false').lower() == 'true'
        
        # Считаем количество связанных курсов
        courses_count = Subject.objects.filter(course_format=format_obj).count()
        
        # Если это не принудительное удаление, возвращаем информацию для подтверждения
        if not force_delete and courses_count > 0:
            return Response({
                'requires_confirmation': True,
                'courses_count': courses_count,
                'message': f'Удаление формата приведет к удалению {courses_count} курсов. Продолжить?'
            }, status=status.HTTP_200_OK)
        
        # Принудительное удаление - удаляем все связанные курсы
        if force_delete:
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

    def get_queryset(self):
        if self.is_swagger_fake_view():
            return CourseFormat.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return CourseFormat.objects.none()
        
        # Проверяем роли пользователя
        user_roles = user.roles.values_list('role', flat=True)
        
        # Администраторы и преподаватели видят все форматы
        if 'admin' in user_roles or 'teacher' in user_roles:
            return CourseFormat.objects.all()
        
        # Студенты видят только форматы опубликованных курсов
        return CourseFormat.objects.filter(
            subjects__is_published=True
        ).distinct()

class SubjectViewSet(SwaggerSafeMixin, BaseLMSViewSet):
    """ViewSet для курсов (предметов)"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filterset_fields = ['is_published', 'category', 'course_format']
    search_fields = ['name', 'description', 'summary']
    ordering_fields = ['creationdate', 'name', 'start_date']
    ordering = ['-creationdate']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Subject.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Subject.objects.none()
            
        queryset = get_user_accessible_subjects(user)
        print(f"🔍 SubjectViewSet.get_queryset() для пользователя: {user.username}")
        print(f"🔍 Возвращаем курсы: {queryset.count()}")
        if queryset.count() > 0:
            print(f"🔍 Первые курсы: {[s.name for s in queryset[:3]]}")
        return queryset
    
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

class EnrollmentViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для записей на курсы"""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'subject']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Enrollment.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Enrollment.objects.none()
            
        return Enrollment.objects.filter(student=user)
    
    def get_serializer_class(self):
        """Используем разные сериализаторы для разных действий"""
        if self.action == 'create':
            return CreateEnrollmentSerializer
        return EnrollmentSerializer

class ThemeViewSet(SwaggerSafeMixin, SubjectRelatedViewSet, ToggleVisibilityMixin, OrderingMixin):
    """ViewSet для тем курсов"""
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer
    filterset_fields = ['subject', 'is_visible']
    ordering_fields = ['sort_order', 'creationdate']
    ordering = ['sort_order']
    
    def get_queryset(self):
        # Переопределяем для тем, так как нужна проверка записи студентов
        if self.is_swagger_fake_view():
            return Theme.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Theme.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        print(f"🔍 ThemeViewSet.get_queryset() для пользователя: {user.username}")
        print(f"🔍 Роли пользователя: {list(user_roles)}")
        
        if 'admin' in user_roles:
            queryset = Theme.objects.all()
            print(f"🔍 Администратор - возвращаем все темы: {queryset.count()}")
            return queryset
        elif 'teacher' in user_roles:
            queryset = Theme.objects.filter(
                Q(subject__teacher=user) | Q(subject__is_published=True)
            ).distinct()
            print(f"🔍 Преподаватель - возвращаем темы: {queryset.count()}")
            return queryset
        else:
            # Студенты видят темы курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            print(f"🔍 Студент записан на курсы: {list(enrolled_subjects)}")
            
            queryset = Theme.objects.filter(subject__in=enrolled_subjects)
            print(f"🔍 Студент - возвращаем темы: {queryset.count()}")
            return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateThemeSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateThemeSerializer
        return ThemeSerializer
    
    def perform_create(self, serializer):
        """Создание темы с проверкой прав"""
        user = self.request.user
        user_roles = user.roles.values_list('role', flat=True)
        subject = serializer.validated_data.get('subject')
        
        print(f"🔍 ThemeViewSet.perform_create() для пользователя: {user.username}")
        print(f"🔍 Роли пользователя: {list(user_roles)}")
        print(f"🔍 Данные для создания темы: {serializer.validated_data}")
        print(f"🔍 Курс для темы: {subject}")
        
        # Проверяем права на создание темы
        if 'admin' not in user_roles:
            if not subject:
                raise ValidationError({'subject': 'Курс обязателен'})
            
            if subject.teacher != user:
                raise PermissionDenied('У вас нет прав для создания темы в этом курсе')
        
        serializer.save()
    
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
    
    @action(detail=False, methods=['post'])
    def reorder_themes(self, request):
        """Изменение порядка тем в курсе"""
        subject_id = request.data.get('subject_id')
        theme_ids = request.data.get('theme_ids', [])
        
        if not subject_id:
            return Response({'error': 'subject_id обязателен'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not theme_ids:
            return Response({'error': 'Список ID тем не может быть пустым'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({'error': 'Курс не найден'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        if 'admin' not in user_roles and subject.teacher != user:
            return Response({'error': 'У вас нет прав для изменения порядка тем'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Обновляем порядок
        for index, theme_id in enumerate(theme_ids):
            try:
                theme = Theme.objects.get(id=theme_id, subject=subject)
                theme.sort_order = index + 1
                theme.save()
            except Theme.DoesNotExist:
                return Response({'error': f'Тема с ID {theme_id} не найдена в этом курсе'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Порядок тем обновлен'}, status=status.HTTP_200_OK)

class LessonViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для уроков"""
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['theme', 'lessontype', 'is_visible']
    ordering_fields = ['sort_order', 'creationdate']
    ordering = ['sort_order']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Lesson.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Lesson.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        print(f"🔍 LessonViewSet.get_queryset() для пользователя: {user.username}")
        print(f"🔍 Роли пользователя: {list(user_roles)}")
        
        if 'admin' in user_roles:
            queryset = Lesson.objects.all()
            print(f"🔍 Администратор - возвращаем все уроки: {queryset.count()}")
            return queryset
        elif 'teacher' in user_roles or hasattr(user, 'teacher'):
            # Преподаватели видят уроки своих курсов + уроки опубликованных курсов
            queryset = Lesson.objects.filter(
                Q(theme__subject__teacher=user) | Q(theme__subject__is_published=True)
            ).distinct()
            print(f"🔍 Преподаватель - возвращаем уроки: {queryset.count()}")
            return queryset
        else:
            # Студенты видят только видимые уроки курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            print(f"🔍 Студент записан на курсы: {list(enrolled_subjects)}")
            
            queryset = Lesson.objects.filter(
                theme__subject__in=enrolled_subjects,
                is_visible=True
            )
            print(f"🔍 Студент - возвращаем видимые уроки: {queryset.count()}")
            return queryset
    
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

class ForumViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для форумов"""
    serializer_class = ForumSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['subject', 'forum_type']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Forum.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Forum.objects.none()
            
        # Проверяем роли пользователя
        user_roles = user.roles.values_list('role', flat=True)
        
        # Админы и модераторы видят все форумы
        if 'admin' in user_roles or 'moderator' in user_roles:
            return Forum.objects.all()
        
        # Учителя видят форумы своих курсов
        if hasattr(user, 'teacher'):
            return Forum.objects.filter(subject__teacher=user)
        
        # Студенты видят форумы курсов, на которые записаны
        enrolled_subjects = Enrollment.objects.filter(
            student=user, status='active'
        ).values_list('subject', flat=True)
        return Forum.objects.filter(subject__in=enrolled_subjects)
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateForumSerializer
        return ForumSerializer

class ForumDiscussionViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для дискуссий форума"""
    serializer_class = ForumDiscussionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['forum', 'is_pinned', 'is_locked']
    search_fields = ['name']
    ordering_fields = ['created_at', 'last_post_at', 'posts_count']
    ordering = ['-is_pinned', '-last_post_at']

    def get_queryset(self):
        if self.is_swagger_fake_view():
            return ForumDiscussion.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return ForumDiscussion.objects.none()
        
        # Проверяем роли пользователя
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return ForumDiscussion.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят дискуссии своих курсов
            return ForumDiscussion.objects.filter(
                forum__subject__teacher=user
            ).distinct()
        else:
            # Студенты видят дискуссии курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return ForumDiscussion.objects.filter(
                forum__subject__in=enrolled_subjects
            ).distinct()

class ForumPostViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для постов форума"""
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['discussion']
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_queryset(self):
        if self.is_swagger_fake_view():
            return ForumPost.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return ForumPost.objects.none()
        
        # Проверяем роли пользователя
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return ForumPost.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят посты своих курсов
            return ForumPost.objects.filter(
                discussion__forum__subject__teacher=user
            ).distinct()
        else:
            # Студенты видят посты курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return ForumPost.objects.filter(
                discussion__forum__subject__in=enrolled_subjects
            ).distinct()

class TestBankViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для банков тестов"""
    serializer_class = TestBankSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['subject']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return TestBank.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return TestBank.objects.none()
            
        if hasattr(user, 'teacher'):
            return TestBank.objects.filter(created_by=user)
        else:
            return TestBank.objects.filter(subject__enrollment__student=user)

class TestViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для тестов"""
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['lesson', 'theme', 'subject', 'type', 'is_active']
    search_fields = ['name', 'title', 'description']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Test.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Test.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return Test.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят тесты своих курсов (привязанные к любому уровню)
            return Test.objects.filter(
                Q(subject__teacher=user) |
                Q(theme__subject__teacher=user) |
                Q(lesson__theme__subject__teacher=user)
            ).distinct()
        else:
            # Студенты видят тесты курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Test.objects.filter(
                Q(subject__in=enrolled_subjects) |
                Q(theme__subject__in=enrolled_subjects) |
                Q(lesson__theme__subject__in=enrolled_subjects),
                is_active=True
            ).distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateTestSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateTestSerializer
        return TestSerializer
    
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
    
    @action(detail=False, methods=['post'])
    def reorder_tests(self, request):
        """Изменение порядка тестов"""
        test_ids = request.data.get('test_ids', [])
        context = request.data.get('context', {})  # {subject_id: id, theme_id: id, lesson_id: id}
        
        if not test_ids:
            return Response({'error': 'Список ID тестов не может быть пустым'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles and 'teacher' not in user_roles:
            return Response({'error': 'У вас нет прав для изменения порядка тестов'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Дополнительная проверка прав для teacher
        if 'admin' not in user_roles:
            # Проверяем, что все тесты принадлежат преподавателю
            for test_id in test_ids:
                try:
                    test = Test.objects.get(id=test_id)
                    # Проверяем права на основе привязки теста
                    has_permission = False
                    if test.subject and test.subject.teacher == user:
                        has_permission = True
                    elif test.theme and test.theme.subject.teacher == user:
                        has_permission = True
                    elif test.lesson and test.lesson.theme.subject.teacher == user:
                        has_permission = True
                    
                    if not has_permission:
                        return Response({'error': f'У вас нет прав на тест с ID {test_id}'}, 
                                      status=status.HTTP_403_FORBIDDEN)
                except Test.DoesNotExist:
                    return Response({'error': f'Тест с ID {test_id} не найден'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
        
        # Обновляем порядок
        for index, test_id in enumerate(test_ids):
            try:
                test = Test.objects.get(id=test_id)
                test.sort_order = index + 1
                test.save()
            except Test.DoesNotExist:
                return Response({'error': f'Тест с ID {test_id} не найден'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Порядок тестов обновлен'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Дублирует тест вместе с вопросами и ответами"""
        from django.db import transaction
        try:
            with transaction.atomic():
                original = self.get_object()
                # Копируем сам тест
                original.pk = None
                original.name = f"{original.name} (копия)"
                original.title = f"{original.title} (копия)"
                original.save()
                new_test = original
                # Копируем вопросы
                questions = Question.objects.filter(test=pk)
                for q in questions:
                    answers = list(q.answers.all())
                    q.pk = None
                    q.test = new_test
                    q.save()
                    # Копируем ответы
                    for a in answers:
                        a.pk = None
                        a.question = q
                        a.save()
                serializer = self.get_serializer(new_test)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TestAttemptViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для попыток прохождения тестов"""
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return TestAttempt.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return TestAttempt.objects.none()
            
        return TestAttempt.objects.filter(student=user)

class AssignmentViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для заданий"""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lesson', 'theme', 'subject']
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'creationdate']
    ordering = ['deadline']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Assignment.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Assignment.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return Assignment.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят задания своих курсов (привязанные к любому уровню)
            return Assignment.objects.filter(
                Q(subject__teacher=user) |
                Q(theme__subject__teacher=user) |
                Q(lesson__theme__subject__teacher=user)
            ).distinct()
        else:
            # Студенты видят задания курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Assignment.objects.filter(
                Q(subject__in=enrolled_subjects) |
                Q(theme__subject__in=enrolled_subjects) |
                Q(lesson__theme__subject__in=enrolled_subjects)
            ).distinct()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateAssignmentSerializer
        return AssignmentSerializer
    
    @action(detail=False, methods=['post'])
    def reorder_assignments(self, request):
        """Изменение порядка заданий"""
        assignment_ids = request.data.get('assignment_ids', [])
        context = request.data.get('context', {})  # {subject_id: id, theme_id: id, lesson_id: id}
        
        if not assignment_ids:
            return Response({'error': 'Список ID заданий не может быть пустым'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем права
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles and 'teacher' not in user_roles:
            return Response({'error': 'У вас нет прав для изменения порядка заданий'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Дополнительная проверка прав для teacher
        if 'admin' not in user_roles:
            # Проверяем, что все задания принадлежат преподавателю
            for assignment_id in assignment_ids:
                try:
                    assignment = Assignment.objects.get(id=assignment_id)
                    # Проверяем права на основе привязки задания
                    has_permission = False
                    if assignment.subject and assignment.subject.teacher == user:
                        has_permission = True
                    elif assignment.theme and assignment.theme.subject.teacher == user:
                        has_permission = True
                    elif assignment.lesson and assignment.lesson.theme.subject.teacher == user:
                        has_permission = True
                    
                    if not has_permission:
                        return Response({'error': f'У вас нет прав на задание с ID {assignment_id}'}, 
                                      status=status.HTTP_403_FORBIDDEN)
                except Assignment.DoesNotExist:
                    return Response({'error': f'Задание с ID {assignment_id} не найдено'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
        
        # Обновляем порядок
        for index, assignment_id in enumerate(assignment_ids):
            try:
                assignment = Assignment.objects.get(id=assignment_id)
                assignment.sort_order = index + 1
                assignment.save()
            except Assignment.DoesNotExist:
                return Response({'error': f'Задание с ID {assignment_id} не найдено'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Порядок заданий обновлен'}, status=status.HTTP_200_OK)

class SubmittedAssignmentViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для сданных заданий"""
    serializer_class = SubmittedAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['assignment', 'grade']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return SubmittedAssignment.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return SubmittedAssignment.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return SubmittedAssignment.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят все сданные задания по своим курсам
            return SubmittedAssignment.objects.filter(
                Q(assignment__subject__teacher=user) |
                Q(assignment__theme__subject__teacher=user) |
                Q(assignment__lesson__theme__subject__teacher=user)
            ).distinct()
        else:
            return SubmittedAssignment.objects.filter(student=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSubmittedAssignmentSerializer
        return SubmittedAssignmentSerializer

class CalendarEventViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для событий календаря"""
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['subject', 'event_type']
    ordering_fields = ['start_date']
    ordering = ['start_date']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return CalendarEvent.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return CalendarEvent.objects.none()
            
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

class BadgeViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для значков"""
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['badge_type', 'subject', 'is_active']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Badge.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Badge.objects.none()
        
        # Проверяем роли пользователя
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return Badge.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят все активные значки
            return Badge.objects.filter(is_active=True)
        else:
            # Студенты видят только значки курсов, на которые они записаны
            enrolled_subjects = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('subject', flat=True)
            return Badge.objects.filter(
                is_active=True,
                subject__in=enrolled_subjects
            ).distinct()

class UserBadgeViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для полученных значков"""
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return UserBadge.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return UserBadge.objects.none()
            
        return UserBadge.objects.filter(user=user)

class NotificationViewSet(SwaggerSafeMixin, BaseLMSViewSet):
    """ViewSet для уведомлений"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filterset_fields = ['is_read', 'notification_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Notification.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Notification.objects.none()
            
        return self.queryset.filter(recipient=user)
    
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

class PrivateMessageViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для личных сообщений"""
    serializer_class = PrivateMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_read']
    search_fields = ['subject', 'content']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return PrivateMessage.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return PrivateMessage.objects.none()
            
        return PrivateMessage.objects.filter(
            Q(sender=user) | Q(recipient=user)
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

    @action(detail=False, methods=['get'])
    def debug_lessons(self, request):
        """Отладочный endpoint для диагностики проблем с уроками"""
        from .models import Subject, Theme, Lesson, Enrollment, UserRole
        
        user = request.user
        user_roles = list(user.roles.values_list('role', flat=True))
        
        debug_info = {
            'user': {
                'username': user.username,
                'id': user.id,
                'roles': user_roles,
                'is_authenticated': user.is_authenticated,
                'has_teacher_attr': hasattr(user, 'teacher')
            },
            'totals': {
                'subjects_total': Subject.objects.count(),
                'themes_total': Theme.objects.count(),
                'lessons_total': Lesson.objects.count(),
                'enrollments_total': Enrollment.objects.count()
            },
            'subjects': {
                'all': Subject.objects.count(),
                'published': Subject.objects.filter(is_published=True).count(),
                'by_user': Subject.objects.filter(teacher=user).count(),
                'accessible_to_user': get_user_accessible_subjects(user).count()
            },
            'themes': {
                'all': Theme.objects.count(),
                'visible': Theme.objects.filter(is_visible=True).count()
            },
            'lessons': {
                'all': Lesson.objects.count(),
                'visible': Lesson.objects.filter(is_visible=True).count()
            },
            'enrollments': {
                'by_user': Enrollment.objects.filter(student=user).count(),
                'active_by_user': Enrollment.objects.filter(student=user, status='active').count()
            }
        }
        
        # Проверяем конкретные данные для первых записей
        first_subjects = list(Subject.objects.all()[:3].values('id', 'name', 'teacher__username', 'is_published'))
        first_themes = list(Theme.objects.all()[:3].values('id', 'name', 'subject__name', 'is_visible'))
        first_lessons = list(Lesson.objects.all()[:3].values('id', 'name', 'theme__name', 'is_visible'))
        
        debug_info['sample_data'] = {
            'subjects': first_subjects,
            'themes': first_themes,
            'lessons': first_lessons
        }
        
        # Проверяем связи между данными
        orphaned_themes = Theme.objects.filter(subject__isnull=True).count()
        orphaned_lessons = Lesson.objects.filter(theme__isnull=True).count()
        
        debug_info['data_integrity'] = {
            'orphaned_themes': orphaned_themes,
            'orphaned_lessons': orphaned_lessons
        }
        
        return Response(debug_info)

class UserRoleViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для ролей пользователей"""
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.is_swagger_fake_view():
            return UserRole.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return UserRole.objects.none()
            
        return UserRole.objects.filter(user=user)
    
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

class QuestionViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для вопросов теста"""
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['test', 'type', 'difficulty']
    search_fields = ['text']
    ordering_fields = ['lastupdate']
    ordering = ['id']
    
    def get_queryset(self):
        """Фильтрация вопросов по правам доступа"""
        if self.is_swagger_fake_view():
            return Question.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Question.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return Question.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят вопросы своих тестов
            return Question.objects.filter(
                Q(test__subject__teacher=user) |
                Q(test__theme__subject__teacher=user) |
                Q(test__lesson__theme__subject__teacher=user)
            ).distinct()
        else:
            # Студенты не могут управлять вопросами
            return Question.objects.none()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateQuestionSerializer
        return QuestionSerializer

class AnswerViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для вариантов ответов"""
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['question', 'is_correct']
    
    def get_queryset(self):
        """Фильтрация ответов по правам доступа"""
        if self.is_swagger_fake_view():
            return Answer.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Answer.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return Answer.objects.all()
        elif 'teacher' in user_roles:
            # Преподаватели видят ответы вопросов своих тестов
            return Answer.objects.filter(
                Q(question__test__subject__teacher=user) |
                Q(question__test__theme__subject__teacher=user) |
                Q(question__test__lesson__theme__subject__teacher=user)
            ).distinct()
        else:
            # Студенты не могут управлять ответами
            return Answer.objects.none()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateAnswerSerializer
        return AnswerSerializer

class ResourceViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для ресурсов (файлов)"""
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject', 'theme', 'lesson', 'file_type', 'is_visible']
    search_fields = ['name', 'description']
    ordering_fields = ['sort_order', 'uploaded_at', 'name']
    ordering = ['sort_order', 'name']
    
    def get_queryset(self):
        """Фильтрация ресурсов по правам доступа"""
        if self.is_swagger_fake_view():
            return Resource.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return Resource.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            # Админы видят все ресурсы
            return Resource.objects.all()
        
        # Получаем доступные курсы для пользователя
        accessible_subjects = get_user_accessible_subjects(user)
        
        # Фильтруем ресурсы по доступным курсам
        return Resource.objects.filter(
            models.Q(subject__in=accessible_subjects) |
            models.Q(theme__subject__in=accessible_subjects) |
            models.Q(lesson__theme__subject__in=accessible_subjects)
        ).filter(is_visible=True).distinct()
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return CreateResourceSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateResourceSerializer
        return ResourceSerializer
    
    def perform_create(self, serializer):
        """Создание ресурса с установкой автора"""
        user = self.request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        print(f"🔍 ResourceViewSet.perform_create() для пользователя: {user.username}")
        print(f"🔍 Роли пользователя: {list(user_roles)}")
        
        # Устанавливаем автора
        serializer.save(uploaded_by=user)
        
        print(f"✅ Ресурс '{serializer.instance.name}' успешно создан")
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Скачивание ресурса"""
        resource = self.get_object()
        
        # Увеличиваем счетчик скачиваний
        resource.download_count += 1
        resource.save()
        
        # Возвращаем URL файла для скачивания
        if resource.file:
            response = HttpResponse(
                resource.file.read(), 
                content_type=resource.file_type
            )
            response['Content-Disposition'] = f'attachment; filename="{resource.name}"'
            return response
        else:
            return Response(
                {'error': 'Файл не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['patch'])
    def toggle_visibility(self, request, pk=None):
        """Переключение видимости ресурса"""
        resource = self.get_object()
        
        # Проверяем права (только автор или преподаватель курса может скрывать/показывать)
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        can_edit = False
        if 'admin' in user_roles:
            can_edit = True
        elif resource.uploaded_by == user:
            can_edit = True
        elif resource.subject and resource.subject.teacher == user:
            can_edit = True
        elif resource.theme and resource.theme.subject.teacher == user:
            can_edit = True
        elif resource.lesson and resource.lesson.theme.subject.teacher == user:
            can_edit = True
        
        if not can_edit:
            return Response(
                {'error': 'У вас нет прав для изменения видимости этого ресурса'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        resource.is_visible = not resource.is_visible
        resource.save()
        
        action_text = 'показан' if resource.is_visible else 'скрыт'
        return Response({
            'message': f'Ресурс "{resource.name}" {action_text}',
            'is_visible': resource.is_visible
        })
    
    @action(detail=False, methods=['get'])
    def by_context(self, request):
        """Получение ресурсов по контексту (курс/тема/урок)"""
        subject_id = request.query_params.get('subject')
        theme_id = request.query_params.get('theme')
        lesson_id = request.query_params.get('lesson')
        
        queryset = self.get_queryset()
        
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        elif theme_id:
            queryset = queryset.filter(theme_id=theme_id, lesson__isnull=True)
        elif subject_id:
            queryset = queryset.filter(subject_id=subject_id, theme__isnull=True, lesson__isnull=True)
        else:
            return Response(
                {'error': 'Необходимо указать subject, theme или lesson'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# ViewSet для унифицированного управления элементами урока
class LessonItemViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """ViewSet для элементов урока (тесты, задания, ресурсы)"""
    serializer_class = LessonItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['lesson', 'item_type']
    ordering_fields = ['sort_order', 'created_at']
    ordering = ['sort_order', 'created_at']
    
    def get_queryset(self):
        """Фильтрация элементов урока по правам доступа"""
        if self.is_swagger_fake_view():
            return LessonItem.objects.none()
            
        user = self.get_safe_user()
        if not user:
            return LessonItem.objects.none()
            
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' in user_roles:
            return LessonItem.objects.all()
        
        # Получаем доступные курсы для пользователя
        accessible_subjects = get_user_accessible_subjects(user)
        
        # Фильтруем элементы по доступным курсам
        return LessonItem.objects.filter(
            lesson__theme__subject__in=accessible_subjects
        ).distinct()
    
    @action(detail=False, methods=['get'])
    def by_lesson(self, request):
        """Получение всех элементов конкретного урока"""
        lesson_id = request.query_params.get('lesson_id')
        
        if not lesson_id:
            return Response(
                {'error': 'Необходимо указать lesson_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lesson_id = int(lesson_id)
        except ValueError:
            return Response(
                {'error': 'Некорректный lesson_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем доступ к уроку
        queryset = self.get_queryset().filter(lesson_id=lesson_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Изменение порядка элементов урока через drag and drop"""
        from .serializers import LessonItemReorderSerializer
        
        serializer = LessonItemReorderSerializer(data=request.data)
        if serializer.is_valid():
            # Проверяем права доступа к уроку
            lesson_id = serializer.validated_data['lesson_id']
            
            try:
                from .models import Lesson
                lesson = Lesson.objects.get(id=lesson_id)
                
                # Проверяем права
                user = request.user
                user_roles = user.roles.values_list('role', flat=True)
                
                can_edit = False
                if 'admin' in user_roles:
                    can_edit = True
                elif 'teacher' in user_roles and lesson.theme.subject.teacher == user:
                    can_edit = True
                
                if not can_edit:
                    return Response(
                        {'error': 'У вас нет прав для изменения порядка элементов в этом уроке'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Обновляем порядок
                updated_items = serializer.save()
                
                # Возвращаем обновленный список
                response_serializer = LessonItemSerializer(updated_items, many=True)
                return Response({
                    'message': 'Порядок элементов урока обновлен',
                    'items': response_serializer.data
                })
                
            except Lesson.DoesNotExist:
                return Response(
                    {'error': 'Урок не найден'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def migrate_existing(self, request):
        """Миграция существующих тестов, заданий и ресурсов в систему LessonItem"""
        from .models import Test, Assignment, Resource, LessonItem
        
        user = request.user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles:
            return Response(
                {'error': 'Только администраторы могут выполнять миграцию'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        created_count = 0
        
        # Миграция тестов, привязанных к урокам
        tests_to_migrate = Test.objects.filter(
            lesson__isnull=False
        ).exclude(
            lesson_items__isnull=False
        )
        
        for test in tests_to_migrate:
            max_order = LessonItem.objects.filter(lesson=test.lesson).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            
            LessonItem.objects.create(
                lesson=test.lesson,
                item_type='test',
                test=test,
                sort_order=(max_order or 0) + 1
            )
            created_count += 1
        
        # Миграция заданий, привязанных к урокам
        assignments_to_migrate = Assignment.objects.filter(
            lesson__isnull=False
        ).exclude(
            lesson_items__isnull=False
        )
        
        for assignment in assignments_to_migrate:
            max_order = LessonItem.objects.filter(lesson=assignment.lesson).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            
            LessonItem.objects.create(
                lesson=assignment.lesson,
                item_type='assignment',
                assignment=assignment,
                sort_order=(max_order or 0) + 1
            )
            created_count += 1
        
        # Миграция ресурсов, привязанных к урокам
        resources_to_migrate = Resource.objects.filter(
            lesson__isnull=False
        ).exclude(
            lesson_items__isnull=False
        )
        
        for resource in resources_to_migrate:
            max_order = LessonItem.objects.filter(lesson=resource.lesson).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            
            LessonItem.objects.create(
                lesson=resource.lesson,
                item_type='resource',
                resource=resource,
                sort_order=(max_order or 0) + 1
            )
            created_count += 1
        
        return Response({
            'message': f'Миграция завершена. Создано {created_count} записей LessonItem',
            'created_count': created_count
        })
