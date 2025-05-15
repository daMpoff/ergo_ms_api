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
    
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Возвращает профиль текущего аутентифицированного работодателя.
        """
        try:
            profile = ExpertsystemCompanyProfile.objects.get(user=request.user)
        except ExpertsystemCompanyProfile.DoesNotExist:
            return Response({'detail': 'Профиль не найден.'}, status=404)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

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
    
    def perform_create(self, serializer):
        company_profile = self.request.user.company_profile
        serializer.save(employer=company_profile)

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

class SetUserSkills(BaseAPIView):
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
            ExpertSystemUserSkill.objects.create(user = userprofile, skill = ess)
        return Response(
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
        expuserskills = ExpertSystemUserSkill.objects.filter(user=userprofile)
        result =[] 
        for expuserskill in expuserskills:     
            result.append({'id':expuserskill.id,'name': expuserskill.skill.name, 'status':expuserskill.status})            
        return Response(
            result,
            status=status.HTTP_200_OK
        )

class CreateTest(BaseAPIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Создание теста экспертной системы",
        responses={
            200: "Тест создан",
            401: "Пользователь не авторизован",
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'title': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Название'),
                'skill': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Навык'),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Описание'),
                'questions': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT),
                    description='вопросы теста')
            }
        )
    )
    def post(self, request:Request):
        title = request.data['title']
        skill = request.data['skill']
        description = request.data['description']
        expskill = ExpertSystemSkill.objects.get(name =skill)
        test = ExpertSystemTest.objects.create(name = title, skill = expskill, descriptions = description)
        questions = request.data['questions']
        for question in questions:
            print(question)
            expquestion =ExpertSystemQuestion.objects.create(text = question['text'], test = test)
            for answer in question['answers']:
                ExpertSystemAnswer.objects.create(text = answer['text'], is_correct = answer['isCorrect'], question = expquestion)
        return Response(status=status.HTTP_200_OK)


class GetAllTests(BaseAPIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Получение всех тестов экспертной системы",
        responses={
            200: "Тесты получены",
            401: "Пользователь не авторизован",
        },
    )
    def get(self, request:Request):
        expstests = ExpertSystemTest.objects.all()
        result =[]
        for exptest in expstests:
            title = exptest.name
            id = exptest.id
            description = exptest.descriptions
            skill = exptest.skill.name
            count_of_questions = len(ExpertSystemQuestion.objects.filter(test = exptest))
            result.append({'id':id,'title':title, 'description':description, 'skill':skill, 'count_of_questions':count_of_questions})
        return Response(result, status=status.HTTP_200_OK)
    

class DeleteTest(BaseAPIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Удаление теста",
        responses={
            200: "Тест удален",
            401: "Пользователь не авторизован",
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='id теста на удаление'),
            }
        )
    )
    def delete(self, request:Request):
        print(request.data)
        id = request.data['id']
        test = ExpertSystemTest.objects.get(id=id)
        for question in ExpertSystemQuestion.objects.filter(test=test):
            for answer in ExpertSystemAnswer.objects.filter(question=question):
                answer.delete()
            question.delete()
        test.delete()
        return Response(status=status.HTTP_200_OK)
