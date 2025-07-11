from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from ..models import (
    Test, TestAttempt, Question, Answer, StudentAnswer,
    StudentAnswerSelection, Student, Teacher
)
from ..serializers import (
    TestSerializer, TestAttemptSerializer, QuestionSerializer,
    AnswerSerializer, StudentAnswerSerializer
)

class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            # Students can see tests for their subjects
            return Test.objects.filter(
                lesson__theme__subject__grade__student=user.student,
                is_active=True
            )
        elif hasattr(user, 'teacher'):
            # Teachers can see all tests they created
            return Test.objects.filter(
                lesson__theme__subject__teacher=user
            )
        return Test.objects.none()

    @action(detail=True, methods=['post'])
    def start_attempt(self, request, pk=None):
        test = self.get_object()
        student = Student.objects.get(user=request.user)
        
        if not test.is_active:
            return Response(
                {"error": "Test is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if student already has an active attempt
        active_attempt = TestAttempt.objects.filter(
            test=test,
            student=student.user,
            status='in_progress'
        ).first()
        
        if active_attempt:
            return Response(
                {"error": "You already have an active attempt"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attempt = TestAttempt.objects.create(
            test=test,
            student=student.user
        )
        serializer = TestAttemptSerializer(attempt)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit_attempt(self, request, pk=None):
        test = self.get_object()
        student = Student.objects.get(user=request.user)
        
        try:
            attempt = TestAttempt.objects.get(
                test=test,
                student=student.user,
                status='in_progress'
            )
        except TestAttempt.DoesNotExist:
            return Response(
                {"error": "No active attempt found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Process answers
        for answer_data in request.data.get('answers', []):
            student_answer = StudentAnswer.objects.create(
                attempt=attempt,
                question_id=answer_data['question_id'],
                text_answer=answer_data.get('text_answer', '')
            )
            
            # Process selections for multiple choice questions
            if answer_data.get('selections'):
                for selection_id in answer_data['selections']:
                    StudentAnswerSelection.objects.create(
                        student_answer=student_answer,
                        answer_id=selection_id
                    )
            
            # Check correctness
            student_answer.check_correctness()
        
        # Calculate final score
        score = attempt.calculate_score()
        attempt.score = score
        attempt.is_passed = score >= test.passing_score
        attempt.status = 'completed'
        attempt.completed_at = timezone.now()
        attempt.save()
        
        serializer = TestAttemptSerializer(attempt)
        return Response(serializer.data)

class TestAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            # Students can see their own attempts
            return TestAttempt.objects.filter(student=user)
        elif hasattr(user, 'teacher'):
            # Teachers can see attempts for their tests
            return TestAttempt.objects.filter(
                test__lesson__theme__subject__teacher=user
            )
        return TestAttempt.objects.none()

    @action(detail=True, methods=['get'])
    def answers(self, request, pk=None):
        attempt = self.get_object()
        answers = StudentAnswer.objects.filter(attempt=attempt)
        serializer = StudentAnswerSerializer(answers, many=True)
        return Response(serializer.data)

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Teachers can see questions for their tests
            return Question.objects.filter(
                test__lesson__theme__subject__teacher=user
            )
        return Question.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def add_answer(self, request, pk=None):
        question = self.get_object()
        answer = Answer.objects.create(
            question=question,
            text=request.data.get('text'),
            is_correct=request.data.get('is_correct', False)
        )
        serializer = AnswerSerializer(answer)
        return Response(serializer.data)

# Создавайте свои представления здесь