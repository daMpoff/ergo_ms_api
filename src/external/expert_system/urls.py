from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExpertSystemStudyGroupViewSet, ExpertSystemStudentProfileViewSet, ExpertsystemCompanyProfileViewSet,
    ExpertSystemSkillViewSet, ExpertSystemUserSkillViewSet, ExpertSystemRoleViewSet,
    ExpertSystemTrajectoryStepViewSet, ExpertSystemOrientationTestViewSet, ExpertSystemOrientationQuestionViewSet,
    ExpertSystemOrientationAnswerViewSet, ExpertSystemTestViewSet, ExpertSystemQuestionViewSet,
    ExpertSystemAnswerViewSet, ExpertSystemTestResultViewSet, ExpertSystemVacancyViewSet,
    ExpertSystemVacancySkillViewSet, ExpertSystemCandidateApplicationViewSet,
    ExpertSystemOrientationTestResultViewSet, ExpertSystemOrientationUserAnswerViewSet,
    SetUserSkills, GetUserSkills, GetUserSkills, CreateTest, GetAllTests, DeleteTest,
    GetTestForRedact, ChangeTest, GetSkillsForCreateTest, GetSkillsForRedactTest,GetTestidBySkill, GetTest,
    TestEvaluation, ExpertSystemCourseViewSet, GetTestResult, GetTestResultBySkillId, DeleteTestResultBySkill,
    ExpertSystemMetricsView, SkillsAnalyticsView, PopularSkillsView,
    StudentsOverviewView, StudentGroupsStatsView, CompaniesVacanciesStatsView,
    PopularVacancySkillsView, TestResultsAnalyticsView, DifficultTestsView,
    StudentActivityTimelineView, RolePopularityStatsView, DashboardSummaryView
)

router = DefaultRouter()
router.register(r'study-groups', ExpertSystemStudyGroupViewSet)
router.register(r'students', ExpertSystemStudentProfileViewSet)
router.register(r'companies', ExpertsystemCompanyProfileViewSet)
router.register(r'skills', ExpertSystemSkillViewSet)
router.register(r'user-skills', ExpertSystemUserSkillViewSet)
router.register(r'roles', ExpertSystemRoleViewSet)
router.register(r'trajectory-steps', ExpertSystemTrajectoryStepViewSet)
router.register(r'orientation-tests', ExpertSystemOrientationTestViewSet)
router.register(r'orientation-questions', ExpertSystemOrientationQuestionViewSet)
router.register(r'orientation-answers', ExpertSystemOrientationAnswerViewSet)
router.register(r'skill-tests', ExpertSystemTestViewSet)
router.register(r'skill-questions', ExpertSystemQuestionViewSet)
router.register(r'skill-answers', ExpertSystemAnswerViewSet)
router.register(r'test-results', ExpertSystemTestResultViewSet)
router.register(r'vacancies', ExpertSystemVacancyViewSet)
router.register(r'vacancy-skills', ExpertSystemVacancySkillViewSet)
router.register(r'applications', ExpertSystemCandidateApplicationViewSet)
router.register(r'orientation-test-results', ExpertSystemOrientationTestResultViewSet)
router.register(r'orientation-user-answers', ExpertSystemOrientationUserAnswerViewSet)
router.register(r'courses', ExpertSystemCourseViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('set-user-skills', SetUserSkills.as_view(), name ='Set user skills'),
    path('get-user-skills', GetUserSkills.as_view(), name ='Get user skills'),
    path('create-test', CreateTest.as_view(), name ='Create test'),
    path('get-all-tests', GetAllTests.as_view(), name='Get all tests'),
    path('delete-test/<int:id>/', DeleteTest.as_view(), name='Delete test'),
    path('get-test', GetTest.as_view(), name='Get test'),
    path('patch-test/<int:id>/', ChangeTest.as_view(), name='Change test'),
    path('get-skills-for-create-test', GetSkillsForCreateTest.as_view(), name='Get skills for create test'),
    path('get-skills-for-redact-test/<int:id>/', GetSkillsForRedactTest.as_view(), name='Get skills for redact test'),
    path('get-test-id-by-skill', GetTestidBySkill.as_view(), name='Get test id by skill'),
    path('get-test-for-redact', GetTestForRedact.as_view(), name='Get test'),
    path('evaluate-test', TestEvaluation.as_view(), name='Evaluate test'),
    path('get-test-result', GetTestResult.as_view(), name='Get test result'),
    path('get-test-result-by-skill-id', GetTestResultBySkillId.as_view(), name='Get test result by skill id'),
    path('delete-test-result-by-skill', DeleteTestResultBySkill.as_view(), name='Delete test result by skill'),
    path('dashboard/metrics/', ExpertSystemMetricsView.as_view(), name='dashboard-metrics'),
    path('dashboard/skills-analytics/', SkillsAnalyticsView.as_view(), name='dashboard-skills-analytics'),
    path('dashboard/popular-skills/', PopularSkillsView.as_view(), name='dashboard-popular-skills'),
    path('dashboard/students-overview/', StudentsOverviewView.as_view(), name='dashboard-students-overview'),
    path('dashboard/student-groups-stats/', StudentGroupsStatsView.as_view(), name='dashboard-student-groups-stats'),
    path('dashboard/companies-vacancies-stats/', CompaniesVacanciesStatsView.as_view(), name='dashboard-companies-vacancies-stats'),
    path('dashboard/popular-vacancy-skills/', PopularVacancySkillsView.as_view(), name='dashboard-popular-vacancy-skills'),
    path('dashboard/test-results-analytics/', TestResultsAnalyticsView.as_view(), name='dashboard-test-results-analytics'),
    path('dashboard/difficult-tests/', DifficultTestsView.as_view(), name='dashboard-difficult-tests'),
    path('dashboard/student-activity-timeline/', StudentActivityTimelineView.as_view(), name='dashboard-student-activity-timeline'),
    path('dashboard/role-popularity-stats/', RolePopularityStatsView.as_view(), name='dashboard-role-popularity-stats'),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
