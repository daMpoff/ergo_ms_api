from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Teacher, Student, StudentGroup, Subject, Grade, Theme,
    Lesson, TestBank, Test, Question, Answer, TestAttempt,
    StudentAnswer, StudentAnswerSelection, Assignment,
    SubmittedAssignment
)

class LMSUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class TeacherSerializer(serializers.ModelSerializer):
    user = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = Teacher
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    user = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = Student
        fields = '__all__'

class StudentGroupSerializer(serializers.ModelSerializer):
    curator = TeacherSerializer(read_only=True)
    
    class Meta:
        model = StudentGroup
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    teacher = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = Subject
        fields = '__all__'

class GradeSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    student = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = Grade
        fields = '__all__'

class ThemeSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    
    class Meta:
        model = Theme
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    theme = ThemeSerializer(read_only=True)
    
    class Meta:
        model = Lesson
        fields = '__all__'

class TestBankSerializer(serializers.ModelSerializer):
    created_by = LMSUserSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    
    class Meta:
        model = TestBank
        fields = '__all__'

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = '__all__'

class TestSerializer(serializers.ModelSerializer):
    lesson = LessonSerializer(read_only=True)
    test_bank = TestBankSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Test
        fields = '__all__'

class StudentAnswerSelectionSerializer(serializers.ModelSerializer):
    answer = AnswerSerializer(read_only=True)
    
    class Meta:
        model = StudentAnswerSelection
        fields = '__all__'

class StudentAnswerSerializer(serializers.ModelSerializer):
    selected_answers = StudentAnswerSelectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = StudentAnswer
        fields = '__all__'

class TestAttemptSerializer(serializers.ModelSerializer):
    test = TestSerializer(read_only=True)
    student = LMSUserSerializer(read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestAttempt
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    lesson = LessonSerializer(read_only=True)
    
    class Meta:
        model = Assignment
        fields = '__all__'

class SubmittedAssignmentSerializer(serializers.ModelSerializer):
    Student = LMSUserSerializer(read_only=True)
    Assignment = AssignmentSerializer(read_only=True)
    
    class Meta:
        model = SubmittedAssignment
        fields = '__all__'
