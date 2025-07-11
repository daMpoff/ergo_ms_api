from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DevelopmentProgramViewSet,
    ProgramTopicViewSet,
    StrategicProjectViewSet,
    ProjectStageViewSet,
    ProjectReportViewSet,
    StageResultViewSet,
    UserProjectRoleViewSet,
    EmployeeWorkloadViewSet,
    ProjectNotificationViewSet
)

router = DefaultRouter()
router.register(r'development-programs', DevelopmentProgramViewSet, basename='development-program')
router.register(r'program-topics', ProgramTopicViewSet, basename='program-topic')
router.register(r'strategic-projects', StrategicProjectViewSet, basename='strategic-project')
router.register(r'project-stages', ProjectStageViewSet, basename='project-stage')
router.register(r'project-reports', ProjectReportViewSet, basename='project-report')
router.register(r'stage-results', StageResultViewSet, basename='stage-result')
router.register(r'user-roles', UserProjectRoleViewSet, basename='user-role')
router.register(r'employee-workload', EmployeeWorkloadViewSet, basename='employee-workload')
router.register(r'project-notifications', ProjectNotificationViewSet, basename='project-notification')

urlpatterns = [
    path('', include(router.urls)),
] 