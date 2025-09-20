from django.urls import path, include
from rest_framework.routers import DefaultRouter

from src.modules.project_ed.views import (
    ProjectViewSet, 
    CategoryViewSet, 
    SubcategoryViewSet, 
    TargetIndicatorViewSet,
    EventBlockViewSet,
    EventViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project-projects')
router.register(r'categories', CategoryViewSet, basename='project-categories')
router.register(r'subcategories', SubcategoryViewSet, basename='project-subcategories')
router.register(r'target-indicators', TargetIndicatorViewSet, basename='project-target-indicators')
router.register(r'event-blocks', EventBlockViewSet, basename='project-event-blocks')
router.register(r'events', EventViewSet, basename='project-events')

urlpatterns = [
    path('project-ed/', include(router.urls)),
]