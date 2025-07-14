from django.urls import path, include

from . import views

urlpatterns = [
    # Test endpoints
    path('tests/', views.TestViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('tests/<int:pk>/', views.TestViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('tests/<int:pk>/start_attempt/', views.TestViewSet.as_view({'post': 'start_attempt'})),
    path('tests/<int:pk>/submit_attempt/', views.TestViewSet.as_view({'post': 'submit_attempt'})),

    # Test Attempt endpoints
    path('attempts/', views.TestAttemptViewSet.as_view({'get': 'list'})),
    path('attempts/<int:pk>/', views.TestAttemptViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update'
    })),
]
