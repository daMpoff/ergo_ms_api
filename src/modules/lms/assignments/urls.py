from django.urls import path, include
from . import views

urlpatterns = [
    # Assignment Management endpoints
    path('management/', views.AssignmentManagementViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('management/<int:pk>/', views.AssignmentManagementViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('management/<int:pk>/submit/', views.AssignmentManagementViewSet.as_view({'post': 'submit'})),

    # Assignment Submission endpoints
    path('submissions/', views.AssignmentSubmissionViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('submissions/<int:pk>/', views.AssignmentSubmissionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('submissions/<int:pk>/grade/', views.AssignmentSubmissionViewSet.as_view({'post': 'grade'})),
]
