from django.urls import path, include
from rest_framework.routers import DefaultRouter

from src.modules.project_ed.views import (
    ProjectViewSet, 
    CategoryViewSet, 
    SubcategoryViewSet, 
    TargetIndicatorViewSet,
    EventBlockViewSet,
    EventViewSet,
    ProjectEdUserProfileViewSet,
    ProjectEdRoleViewSet,
    ProjectEdPositionViewSet,
    ProjectEdFacultyViewSet,
    ProjectEdDepartmentViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project-projects')
router.register(r'categories', CategoryViewSet, basename='project-categories')
router.register(r'subcategories', SubcategoryViewSet, basename='project-subcategories')
router.register(r'target-indicators', TargetIndicatorViewSet, basename='project-target-indicators')
router.register(r'event-blocks', EventBlockViewSet, basename='project-event-blocks')
router.register(r'events', EventViewSet, basename='project-events')
router.register(r'user-profiles', ProjectEdUserProfileViewSet, basename='project-user-profiles')
router.register(r'roles', ProjectEdRoleViewSet, basename='project-ed-roles')
router.register(r'positions', ProjectEdPositionViewSet, basename='project-ed-positions')
router.register(r'faculties', ProjectEdFacultyViewSet, basename='project-ed-faculties')
router.register(r'departments', ProjectEdDepartmentViewSet, basename='project-ed-departments')

urlpatterns = [
    path('', include(router.urls)),
]