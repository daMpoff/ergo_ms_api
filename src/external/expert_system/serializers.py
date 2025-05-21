from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.models import User
from .models import (
    ExpertSystemStudyGroup, ExpertSystemStudentProfile, ExpertsystemCompanyProfile,
    ExpertSystemSkill, ExpertSystemUserSkill, ExpertSystemRole,
    ExpertSystemTrajectoryStep, ExpertSystemOrientationTest, ExpertSystemOrientationQuestion,
    ExpertSystemOrientationAnswer, ExpertSystemTest, ExpertSystemQuestion, ExpertSystemAnswer,
    ExpertSystemTestResult, ExpertSystemVacancy, ExpertSystemVacancySkill,
    ExpertSystemCandidateApplication, ExpertSystemOrientationTestResult,
    ExpertSystemOrientationUserAnswer
)

class ExpertSystemUserSkillSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemStudentProfile.objects.all())
    skill = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemSkill.objects.all())

    class Meta:
        model = ExpertSystemUserSkill
        fields = ['id', 'user', 'skill', 'status']
        
class ExpertSystemStudyGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertSystemStudyGroup
        fields = '__all__'

class ExpertSystemSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertSystemSkill
        fields = '__all__'
        
class ExpertSystemVacancySerializer(serializers.ModelSerializer):
    required_skills = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=ExpertSystemSkill.objects.all()
    )
    required_skills_info = ExpertSystemSkillSerializer(
        many=True,
        read_only=True,
        source='required_skills'
    )
    employer_name = serializers.CharField(
        source='employer.company_name',
        read_only=True
    )

    class Meta:
        model = ExpertSystemVacancy
        fields = [
            'id',
            'employer',
            'title',
            'employer_name',
            'description',
            'required_skills',
            'required_skills_info'
        ]
        read_only_fields = ['employer']

    def create(self, validated_data):
        skills = validated_data.pop('required_skills', [])
        with transaction.atomic():
            vacancy = ExpertSystemVacancy.objects.create(**validated_data)
            for skill in skills:
                ExpertSystemVacancySkill.objects.create(
                    vacancy=vacancy,
                    skill=skill,
                    is_mandatory=True
                )
        return vacancy

    def update(self, instance, validated_data):
        skills = validated_data.pop('required_skills', None)

        # обновляем все прочие поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if skills is not None:
            with transaction.atomic():
                # удаляем старые связи
                ExpertSystemVacancySkill.objects.filter(vacancy=instance).delete()
                # создаем новые
                for skill in skills:
                    ExpertSystemVacancySkill.objects.create(
                        vacancy=instance,
                        skill=skill,
                        is_mandatory=True
                    )
        return instance
class ExpertSystemStudentProfileSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # write_only — ждёт в запросе числовой ID
    study_group = serializers.PrimaryKeyRelatedField(
        queryset=ExpertSystemStudyGroup.objects.all(),
        allow_null=True,
        write_only=True
    )
    # read_only — отдаёт в ответе только имя группы
    group_name = serializers.CharField(
        source='study_group.name',
        read_only=True,
        default=''
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ExpertSystemStudentProfile
        fields = [
            'id', 'user',
            'first_name', 'last_name',
            'study_group', 'group_name',
            'has_experience',
            'email', 'phone'
        ]

class ExpertsystemCompanyProfileSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    vacancies = ExpertSystemVacancySerializer(
        many=True, 
        read_only=True,
    )
    class Meta:
        model = ExpertsystemCompanyProfile
        fields = [
            'id', 'user', 'company_name', 'description', 'website',
            'contact_person', 'contact_email', 'is_verified', 'vacancies'
        ]

class ExpertSystemRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertSystemRole
        fields = '__all__'

class ExpertSystemTrajectoryStepSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemRole.objects.all())

    class Meta:
        model = ExpertSystemTrajectoryStep
        fields = ['id', 'role', 'order', 'description']

class ExpertSystemOrientationTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertSystemOrientationTest
        fields = '__all__'

class ExpertSystemOrientationQuestionSerializer(serializers.ModelSerializer):
    test = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemOrientationTest.objects.all())

    class Meta:
        model = ExpertSystemOrientationQuestion
        fields = ['id', 'test', 'text']

class ExpertSystemOrientationAnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemOrientationQuestion.objects.all())
    role = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemRole.objects.all())

    class Meta:
        model = ExpertSystemOrientationAnswer
        fields = ['id', 'question', 'text', 'weight', 'role']

class ExpertSystemTestSerializer(serializers.ModelSerializer):
    skill = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemSkill.objects.all())

    class Meta:
        model = ExpertSystemTest
        fields = ['id', 'skill', 'name']

class ExpertSystemQuestionSerializer(serializers.ModelSerializer):
    test = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemTest.objects.all())

    class Meta:
        model = ExpertSystemQuestion
        fields = ['id', 'test', 'text']

class ExpertSystemAnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemQuestion.objects.all())

    class Meta:
        model = ExpertSystemAnswer
        fields = ['id', 'question', 'text', 'is_correct']

class ExpertSystemTestResultSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemStudentProfile.objects.all())
    test = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemTest.objects.all())

    class Meta:
        model = ExpertSystemTestResult
        fields = ['id', 'user', 'test', 'score', 'passed']

class ExpertSystemVacancySkillSerializer(serializers.ModelSerializer):
    vacancy = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemVacancy.objects.all())
    skill = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemSkill.objects.all())

    class Meta:
        model = ExpertSystemVacancySkill
        fields = ['id', 'vacancy', 'skill', 'is_mandatory']

class ExpertSystemCandidateApplicationSerializer(serializers.ModelSerializer):
    vacancy = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemVacancy.objects.all())
    candidate = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemStudentProfile.objects.all())

    class Meta:
        model = ExpertSystemCandidateApplication
        fields = ['id', 'vacancy', 'candidate', 'applied_at', 'match_score']

class ExpertSystemOrientationTestResultSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemStudentProfile.objects.all())
    test = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemOrientationTest.objects.all())
    best_role = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemRole.objects.all(), allow_null=True)

    class Meta:
        model = ExpertSystemOrientationTestResult
        fields = ['id', 'user', 'test', 'taken_at', 'best_role', 'best_score']

class ExpertSystemOrientationUserAnswerSerializer(serializers.ModelSerializer):
    result = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemOrientationTestResult.objects.all())
    question = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemOrientationQuestion.objects.all())
    answer = serializers.PrimaryKeyRelatedField(queryset=ExpertSystemOrientationAnswer.objects.all())

    class Meta:
        model = ExpertSystemOrientationUserAnswer
        fields = ['id', 'result', 'question', 'answer']
