from django.urls import path, include
from . import views

urlpatterns = [
    # Teacher endpoints
    path('teachers/', views.TeacherViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('teachers/<int:pk>/', views.TeacherViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('teachers/<int:pk>/subjects/', views.TeacherViewSet.as_view({'get': 'subjects'})),
    path('teachers/<int:pk>/student_groups/', views.TeacherViewSet.as_view({'get': 'student_groups'})),

    # Student endpoints
    path('students/', views.StudentViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('students/<int:pk>/', views.StudentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('students/<int:pk>/grades/', views.StudentViewSet.as_view({'get': 'grades'})),
    path('students/<int:pk>/test_attempts/', views.StudentViewSet.as_view({'get': 'test_attempts'})),

    # Student Group endpoints
    path('groups/', views.StudentGroupViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('groups/<int:pk>/', views.StudentGroupViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('groups/<int:pk>/students/', views.StudentGroupViewSet.as_view({'get': 'students'})),
]
