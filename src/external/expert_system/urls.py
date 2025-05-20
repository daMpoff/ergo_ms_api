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
    TestEvaluation
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
router.register(r'orientation-results', ExpertSystemOrientationTestResultViewSet)
router.register(r'orientation-answers', ExpertSystemOrientationUserAnswerViewSet)


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
    path('evaluate-test', TestEvaluation.as_view(), name='Evaluate test')
]