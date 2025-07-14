from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.modules.lms.views import (
    AnalyticsViewSet, UserProfileViewSet, CourseCategoryViewSet,
    CourseFormatViewSet, SubjectViewSet, EnrollmentViewSet, 
    ThemeViewSet, LessonViewSet, ResourceViewSet, ForumViewSet, ForumDiscussionViewSet, 
    ForumPostViewSet, TestBankViewSet, TestViewSet, TestAttemptViewSet,
    AssignmentViewSet, SubmittedAssignmentViewSet,
    CalendarEventViewSet, BadgeViewSet, UserBadgeViewSet,
    NotificationViewSet, PrivateMessageViewSet, UserRoleViewSet,
    QuestionViewSet, AnswerViewSet, LessonItemViewSet
)

# Создаем роутер для API
router = DefaultRouter()

# Регистрируем ViewSet'ы
router.register(r'profiles', UserProfileViewSet, basename='userprofile')
router.register(r'user-roles', UserRoleViewSet, basename='userrole')
router.register(r'categories', CourseCategoryViewSet, basename='coursecategory')
router.register(r'course-formats', CourseFormatViewSet, basename='courseformat')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'themes', ThemeViewSet, basename='theme')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'lesson-items', LessonItemViewSet, basename='lessonitem')
router.register(r'resources', ResourceViewSet, basename='resource')
router.register(r'forums', ForumViewSet, basename='forum')
router.register(r'discussions', ForumDiscussionViewSet, basename='forumdiscussion')
router.register(r'posts', ForumPostViewSet, basename='forumpost')
router.register(r'test-banks', TestBankViewSet, basename='testbank')
router.register(r'tests', TestViewSet, basename='test')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'answers', AnswerViewSet, basename='answer')
router.register(r'test-attempts', TestAttemptViewSet, basename='testattempt')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submitted-assignments', SubmittedAssignmentViewSet, basename='submittedassignment')
router.register(r'calendar', CalendarEventViewSet, basename='calendarevent')
router.register(r'badges', BadgeViewSet, basename='badge')
router.register(r'user-badges', UserBadgeViewSet, basename='userbadge')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'messages', PrivateMessageViewSet, basename='privatemessage')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Дополнительные специфичные endpoints
    path('analytics/student/', AnalyticsViewSet.as_view({'get': 'student_stats'}), name='student-analytics'),
    path('analytics/teacher/', AnalyticsViewSet.as_view({'get': 'teacher_stats'}), name='teacher-analytics'),
    path('analytics/dashboard/', AnalyticsViewSet.as_view({'get': 'dashboard'}), name='dashboard'),
    path('analytics/debug-lessons/', AnalyticsViewSet.as_view({'get': 'debug_lessons'}), name='debug-lessons'),
    
    # Endpoints для профиля
    path('profile/me/', UserProfileViewSet.as_view({'get': 'my_profile', 'patch': 'my_profile'}), name='my-profile'),
    
    # Endpoints для ролей
    path('user/roles/', UserRoleViewSet.as_view({'get': 'current'}), name='user-roles'),
    path('user/roles/switch/', UserRoleViewSet.as_view({'post': 'switch_role'}), name='switch-role'),
    
    # Endpoints для курсов
    path('subjects/<int:pk>/enroll/', SubjectViewSet.as_view({'post': 'enroll'}), name='subject-enroll'),
    path('subjects/<int:pk>/unenroll/', SubjectViewSet.as_view({'delete': 'unenroll'}), name='subject-unenroll'),
    path('subjects/<int:pk>/students/', SubjectViewSet.as_view({'get': 'enrolled_students'}), name='subject-students'),
    path('subjects/<int:pk>/duplicate/', SubjectViewSet.as_view({'post': 'duplicate'}), name='subject-duplicate'),
    path('subjects/<int:pk>/toggle-published/', SubjectViewSet.as_view({'patch': 'toggle_published'}), name='subject-toggle-published'),
    path('subjects/<int:pk>/structure/', SubjectViewSet.as_view({'get': 'structure'}), name='subject-structure'),
    
    # Endpoints для тем
    path('themes/<int:pk>/reorder-lessons/', ThemeViewSet.as_view({'post': 'reorder_lessons'}), name='theme-reorder-lessons'),
    path('themes/reorder-themes/', ThemeViewSet.as_view({'post': 'reorder_themes'}), name='reorder-themes'),
    
    # Endpoints для уроков
    path('lessons/<int:pk>/duplicate/', LessonViewSet.as_view({'post': 'duplicate'}), name='lesson-duplicate'),
    path('lessons/<int:pk>/toggle-visibility/', LessonViewSet.as_view({'patch': 'toggle_visibility'}), name='lesson-toggle-visibility'),
    path('lessons/by-course/', LessonViewSet.as_view({'get': 'by_course'}), name='lessons-by-course'),
    
    # Endpoints для элементов урока (тесты, задания, ресурсы)
    path('lesson-items/by-lesson/', LessonItemViewSet.as_view({'get': 'by_lesson'}), name='lesson-items-by-lesson'),
    path('lesson-items/reorder/', LessonItemViewSet.as_view({'post': 'reorder'}), name='lesson-items-reorder'),
    path('lesson-items/migrate/', LessonItemViewSet.as_view({'post': 'migrate_existing'}), name='lesson-items-migrate'),
    
    # Endpoints для ресурсов
    path('resources/<int:pk>/download/', ResourceViewSet.as_view({'get': 'download'}), name='resource-download'),
    path('resources/<int:pk>/toggle-visibility/', ResourceViewSet.as_view({'patch': 'toggle_visibility'}), name='resource-toggle-visibility'),
    path('resources/by-context/', ResourceViewSet.as_view({'get': 'by_context'}), name='resources-by-context'),
    
    # Endpoints для тестов
    path('tests/<int:pk>/start/', TestViewSet.as_view({'post': 'start_attempt'}), name='test-start-attempt'),
    
    # Endpoints для календаря
    path('calendar/upcoming/', CalendarEventViewSet.as_view({'get': 'upcoming'}), name='calendar-upcoming'),
    
    # Endpoints для уведомлений
    path('notifications/<int:pk>/read/', NotificationViewSet.as_view({'patch': 'mark_as_read'}), name='notification-read'),
    path('notifications/read-all/', NotificationViewSet.as_view({'patch': 'mark_all_as_read'}), name='notifications-read-all'),
]
