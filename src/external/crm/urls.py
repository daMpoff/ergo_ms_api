from django.urls import path
from .views import (
    MonthlyStatsView, PriorityStatsView, SectionStatsView,
    ProjectViewSet, SectionViewSet, TaskViewSet,
    CalendarViewSet, UserProjectViewSet, UserViewSet,
    ProjectCompletionStatsView, UserProductivityStatsView,
    DeadlineAnalysisView, TaskCreationTrendView,
    ProjectTimelineStatsView, CalendarActivityStatsView,
    TaskComplexityStatsView
)

# Project
project_list = ProjectViewSet.as_view({'get': 'list', 'post': 'create'})
project_detail = ProjectViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
project_bulk_create = ProjectViewSet.as_view({'post': 'bulk_create'})
project_delete_all = ProjectViewSet.as_view({'delete': 'delete_all'})

# Section
section_list = SectionViewSet.as_view({'get': 'list', 'post': 'create'})
section_detail = SectionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
section_bulk_create = SectionViewSet.as_view({'post': 'bulk_create'})
section_delete_all = SectionViewSet.as_view({'delete': 'delete_all'})

# Task
task_list = TaskViewSet.as_view({'get': 'list', 'post': 'create'})
task_detail = TaskViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
task_bulk_create = TaskViewSet.as_view({'post': 'bulk_create'})
task_delete_all = TaskViewSet.as_view({'delete': 'delete_all'})

# Calendar
calendar_list = CalendarViewSet.as_view({'get': 'list', 'post': 'create'})
calendar_detail = CalendarViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
calendar_bulk_create = CalendarViewSet.as_view({'post': 'bulk_create'})
calendar_delete_all = CalendarViewSet.as_view({'delete': 'delete_all'})

# UserProject
userproject_list = UserProjectViewSet.as_view({'get': 'list', 'post': 'create'})
userproject_detail = UserProjectViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
userproject_bulk_create = UserProjectViewSet.as_view({'post': 'bulk_create'})
userproject_delete_all = UserProjectViewSet.as_view({'delete': 'delete_all'})

# User
user_list = UserViewSet.as_view({'get': 'list', 'post': 'create'})
user_detail = UserViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
user_bulk_create = UserViewSet.as_view({'post': 'bulk_create'})
user_delete_all = UserViewSet.as_view({'delete': 'delete_all'})

urlpatterns = [
    path('stats/monthly/', MonthlyStatsView.as_view(), name='monthly-stats'),
    path('stats/priority/', PriorityStatsView.as_view(), name='priority-stats'),
    path('stats/sections/', SectionStatsView.as_view(), name='section-stats'),
    path('stats/project-completion/', ProjectCompletionStatsView.as_view(), name='project-completion-stats'),
    path('stats/user-productivity/', UserProductivityStatsView.as_view(), name='user-productivity-stats'),
    path('stats/deadline-analysis/', DeadlineAnalysisView.as_view(), name='deadline-analysis-stats'),
    path('stats/task-creation-trend/', TaskCreationTrendView.as_view(), name='task-creation-trend-stats'),
    path('stats/project-timeline/', ProjectTimelineStatsView.as_view(), name='project-timeline-stats'),
    path('stats/calendar-activity/', CalendarActivityStatsView.as_view(), name='calendar-activity-stats'),
    path('stats/task-complexity/', TaskComplexityStatsView.as_view(), name='task-complexity-stats'),

    # Project
    path('projects/', project_list, name='project-list'),
    path('projects/<int:pk>/', project_detail, name='project-detail'),
    path('projects/bulk_create/', project_bulk_create, name='project-bulk-create'),
    path('projects/delete_all/', project_delete_all, name='project-delete-all'),

    # Section
    path('sections/', section_list, name='section-list'),
    path('sections/<int:pk>/', section_detail, name='section-detail'),
    path('sections/bulk_create/', section_bulk_create, name='section-bulk-create'),
    path('sections/delete_all/', section_delete_all, name='section-delete-all'),

    # Task
    path('tasks/', task_list, name='task-list'),
    path('tasks/<int:pk>/', task_detail, name='task-detail'),
    path('tasks/bulk_create/', task_bulk_create, name='task-bulk-create'),
    path('tasks/delete_all/', task_delete_all, name='task-delete-all'),

    # Calendar
    path('calendars/', calendar_list, name='calendar-list'),
    path('calendars/<int:pk>/', calendar_detail, name='calendar-detail'),
    path('calendars/bulk_create/', calendar_bulk_create, name='calendar-bulk-create'),
    path('calendars/delete_all/', calendar_delete_all, name='calendar-delete-all'),

    # UserProject
    path('user-projects/', userproject_list, name='userproject-list'),
    path('user-projects/<int:pk>/', userproject_detail, name='userproject-detail'),
    path('user-projects/bulk_create/', userproject_bulk_create, name='userproject-bulk-create'),
    path('user-projects/delete_all/', userproject_delete_all, name='userproject-delete-all'),

    # User
    path('users/', user_list, name='user-list'),
    path('users/<int:pk>/', user_detail, name='user-detail'),
    path('users/bulk_create/', user_bulk_create, name='user-bulk-create'),
    path('users/delete_all/', user_delete_all, name='user-delete-all'),
    # Здесь могут быть другие маршруты для CRM модуля
]