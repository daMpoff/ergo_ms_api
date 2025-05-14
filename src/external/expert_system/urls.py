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
    SetUserSkillTest, GetUserSkillTest, GetUserSkills
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
    path('set-user-skill-test', SetUserSkillTest.as_view(), name ='Set user skill test'),
    path('get-user-skill-tests', GetUserSkillTest.as_view(), name ='Get user skill tests'),
    path('get-user-skills', GetUserSkills.as_view(), name ='Get user skills')
]
