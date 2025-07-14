from django.urls import path, include
from . import views

urlpatterns = [
    # Subject endpoints
    path('subjects/', views.SubjectViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('subjects/<int:pk>/', views.SubjectViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('subjects/<int:pk>/themes/', views.SubjectViewSet.as_view({'get': 'themes'})),
    path('subjects/<int:pk>/grades/', views.SubjectViewSet.as_view({'get': 'grades'})),

    # Theme endpoints
    path('themes/', views.ThemeViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('themes/<int:pk>/', views.ThemeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('themes/<int:pk>/lessons/', views.ThemeViewSet.as_view({'get': 'lessons'})),

    # Lesson endpoints
    path('lessons/', views.LessonViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('lessons/<int:pk>/', views.LessonViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('lessons/<int:pk>/tests/', views.LessonViewSet.as_view({'get': 'tests'})),
    path('lessons/<int:pk>/assignments/', views.LessonViewSet.as_view({'get': 'assignments'})),
]
