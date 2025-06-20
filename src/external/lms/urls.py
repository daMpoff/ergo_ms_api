from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.external.lms.views import (
    AnalyticsViewSet, UserProfileViewSet, CourseCategoryViewSet,
    CourseFormatViewSet, SubjectViewSet, EnrollmentViewSet, 
    ThemeViewSet, LessonViewSet, ForumViewSet, ForumDiscussionViewSet, 
    ForumPostViewSet, TestBankViewSet, TestViewSet, TestAttemptViewSet,
    AssignmentViewSet, SubmittedAssignmentViewSet,
    CalendarEventViewSet, BadgeViewSet, UserBadgeViewSet,
    NotificationViewSet, PrivateMessageViewSet, UserRoleViewSet
)

app_name = 'lms'

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
router.register(r'forums', ForumViewSet, basename='forum')
router.register(r'discussions', ForumDiscussionViewSet, basename='forumdiscussion')
router.register(r'posts', ForumPostViewSet, basename='forumpost')
router.register(r'test-banks', TestBankViewSet, basename='testbank')
router.register(r'tests', TestViewSet, basename='test')
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
    path('api/', include(router.urls)),
    
    # Дополнительные специфичные endpoints
    path('analytics/student/', AnalyticsViewSet.as_view({'get': 'student_stats'}), name='student-analytics'),
    path('analytics/teacher/', AnalyticsViewSet.as_view({'get': 'teacher_stats'}), name='teacher-analytics'),
    path('analytics/dashboard/', AnalyticsViewSet.as_view({'get': 'dashboard'}), name='dashboard'),
    
    # Endpoints для профиля
    path('profile/me/', UserProfileViewSet.as_view({'get': 'my_profile', 'patch': 'my_profile'}), name='my-profile'),
    
    # Endpoints для ролей
    path('user/roles/', UserRoleViewSet.as_view({'get': 'current'}), name='user-roles'),
    path('user/roles/switch/', UserRoleViewSet.as_view({'post': 'switch_role'}), name='switch-role'),
    
    # Endpoints для курсов
    path('subjects/<int:pk>/enroll/', SubjectViewSet.as_view({'post': 'enroll'}), name='subject-enroll'),
    path('subjects/<int:pk>/unenroll/', SubjectViewSet.as_view({'delete': 'unenroll'}), name='subject-unenroll'),
    path('subjects/<int:pk>/students/', SubjectViewSet.as_view({'get': 'enrolled_students'}), name='subject-students'),
    
    # Endpoints для тестов
    path('tests/<int:pk>/start/', TestViewSet.as_view({'post': 'start_attempt'}), name='test-start-attempt'),
    
    # Endpoints для календаря
    path('calendar/upcoming/', CalendarEventViewSet.as_view({'get': 'upcoming'}), name='calendar-upcoming'),
    
    # Endpoints для уведомлений
    path('notifications/<int:pk>/read/', NotificationViewSet.as_view({'patch': 'mark_as_read'}), name='notification-read'),
    path('notifications/read-all/', NotificationViewSet.as_view({'patch': 'mark_all_as_read'}), name='notifications-read-all'),
]
