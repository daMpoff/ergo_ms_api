from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import (
    ExpertSystemStudyGroup, ExpertSystemStudentProfile, ExpertsystemCompanyProfile,
    ExpertSystemSkill, ExpertSystemUserSkill, ExpertSystemRole,
    ExpertSystemTrajectoryStep, ExpertSystemOrientationTest, ExpertSystemOrientationQuestion,
    ExpertSystemOrientationAnswer, ExpertSystemTest, ExpertSystemQuestion, ExpertSystemAnswer,
    ExpertSystemTestResult, ExpertSystemVacancy, ExpertSystemVacancySkill,
    ExpertSystemCandidateApplication, ExpertSystemOrientationTestResult,
    ExpertSystemOrientationUserAnswer
)

from .serializers import (
    ExpertSystemStudyGroupSerializer, ExpertSystemStudentProfileSerializer, ExpertsystemCompanyProfileSerializer,
    ExpertSystemSkillSerializer, ExpertSystemUserSkillSerializer, ExpertSystemRoleSerializer,
    ExpertSystemTrajectoryStepSerializer, ExpertSystemOrientationTestSerializer, ExpertSystemOrientationQuestionSerializer,
    ExpertSystemOrientationAnswerSerializer, ExpertSystemTestSerializer, ExpertSystemQuestionSerializer,
    ExpertSystemAnswerSerializer, ExpertSystemTestResultSerializer, ExpertSystemVacancySerializer,
    ExpertSystemVacancySkillSerializer, ExpertSystemCandidateApplicationSerializer,
    ExpertSystemOrientationTestResultSerializer, ExpertSystemOrientationUserAnswerSerializer
)

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from src.core.utils.base.base_views import BaseAPIView
from rest_framework.request import Request
class ExpertSystemStudyGroupViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemStudyGroup.objects.all()
    serializer_class = ExpertSystemStudyGroupSerializer

class ExpertSystemStudentProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemStudentProfile.objects.select_related('user', 'study_group').all()
    serializer_class = ExpertSystemStudentProfileSerializer
    
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Возвращает профиль текущего аутентифицированного студента
        """
        try:
            profile = ExpertSystemStudentProfile.objects.get(user=request.user)
        except ExpertSystemStudentProfile.DoesNotExist:
            return Response({'detail': 'Профиль не найден.'}, status=404)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

class ExpertsystemCompanyProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertsystemCompanyProfile.objects.select_related('user').all()
    serializer_class = ExpertsystemCompanyProfileSerializer

class ExpertSystemSkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemSkill.objects.all()
    serializer_class = ExpertSystemSkillSerializer

class ExpertSystemUserSkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemUserSkill.objects.select_related('user', 'skill').all()
    serializer_class = ExpertSystemUserSkillSerializer

class ExpertSystemRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemRole.objects.all()
    serializer_class = ExpertSystemRoleSerializer

class ExpertSystemTrajectoryStepViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemTrajectoryStep.objects.select_related('role').all()
    serializer_class = ExpertSystemTrajectoryStepSerializer

class ExpertSystemOrientationTestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemOrientationTest.objects.all()
    serializer_class = ExpertSystemOrientationTestSerializer

class ExpertSystemOrientationQuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemOrientationQuestion.objects.select_related('test').all()
    serializer_class = ExpertSystemOrientationQuestionSerializer

class ExpertSystemOrientationAnswerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemOrientationAnswer.objects.select_related('question', 'role').all()
    serializer_class = ExpertSystemOrientationAnswerSerializer

class ExpertSystemTestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemTest.objects.select_related('skill').all()
    serializer_class = ExpertSystemTestSerializer

class ExpertSystemQuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemQuestion.objects.select_related('test').all()
    serializer_class = ExpertSystemQuestionSerializer

class ExpertSystemAnswerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemAnswer.objects.select_related('question').all()
    serializer_class = ExpertSystemAnswerSerializer

class ExpertSystemTestResultViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemTestResult.objects.select_related('user', 'test').all()
    serializer_class = ExpertSystemTestResultSerializer

class ExpertSystemVacancyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemVacancy.objects.select_related('employer').prefetch_related('required_skills').all()
    serializer_class = ExpertSystemVacancySerializer

class ExpertSystemVacancySkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemVacancySkill.objects.select_related('vacancy', 'skill').all()
    serializer_class = ExpertSystemVacancySkillSerializer

class ExpertSystemCandidateApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemCandidateApplication.objects.select_related('vacancy', 'candidate').all()
    serializer_class = ExpertSystemCandidateApplicationSerializer

class ExpertSystemOrientationTestResultViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemOrientationTestResult.objects.select_related('user', 'test', 'best_role').all()
    serializer_class = ExpertSystemOrientationTestResultSerializer

class ExpertSystemOrientationUserAnswerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ExpertSystemOrientationUserAnswer.objects.select_related('result', 'question', 'answer').all()
    serializer_class = ExpertSystemOrientationUserAnswerSerializer

class SetUserSkillTest(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Установление тестов по умениям",
        responses={
            200: "Права пользователя",
            401: "Пользователь не авторизован",
            403: "Нет доступа"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Skills': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING), 
                    description='Навыки'
                )
            }
        )
    )
    def post(self, request: Request):
        user = request.user
        userprofile = ExpertSystemStudentProfile.objects.get(user=user)
        skill_names = request.data['Skills']
        for skill_name in skill_names:
            ess = ExpertSystemSkill.objects.get(name= skill_name)
            esst = ExpertSystemTest.objects.get(skill = ess)
            ExpertSystemTestResult.objects.create(test = esst, user = userprofile, score = 0, passed = False)
            
        return Response(
            status=status.HTTP_200_OK
        )
    
class GetUserSkillTests(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение тестов по навыкам пользователя",
        responses={
            200: "Тесты пользователя по навыкам получены",
            401: "Пользователь не авторизован",
        },
    )
    def get(self, request: Request):
        user = request.user
        userprofile = ExpertSystemStudentProfile.objects.get(user=user)
        exptestresults = ExpertSystemTestResult.objects.filter(user= userprofile)
        result = []
        for exptestresult in exptestresults:
            test = exptestresult.test       
            testname = test.name
            description = test.descriptions
            result.append({'id':exptestresult.id, 'test':testname,'description':description, 'result': exptestresult.score,'status': exptestresult.passed})
            
        return Response(
            result,
            status=status.HTTP_200_OK
        )
    
class GetUserSkills(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение навыков пользователя",
        responses={
            200: "навыки получены",
            401: "Пользователь не авторизован",
        },
    )
    def get(self, request: Request):
        user = request.user
        userprofile = ExpertSystemStudentProfile.objects.get(user=user)
        exptestresults = ExpertSystemTestResult.objects.filter(user= userprofile)
        result = []
        for exptestresult in exptestresults:
            test = exptestresult.test     
            result.append(test.skill.name)            
        return Response(
            result,
            status=status.HTTP_200_OK
        )
    
class GetTestbySkill(BaseAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение навыков пользователя",
        responses={
            200: "навыки получены",
            401: "Пользователь не авторизован",
        },
    )
    def get(self, request: Request):
        user = request.user
        userprofile = ExpertSystemStudentProfile.objects.get(user=user)
        exptestresults = ExpertSystemTestResult.objects.filter(user= userprofile)
        result = []
        for exptestresult in exptestresults:
            test = exptestresult.test     
            result.append(test.skill.name)            
        return Response(
            result,
            status=status.HTTP_200_OK
        )