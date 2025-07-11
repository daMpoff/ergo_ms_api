from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from ..models import Assignment, SubmittedAssignment, Student, Teacher
from ..serializers import AssignmentSerializer, SubmittedAssignmentSerializer

class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = SubmittedAssignment.objects.all()
    serializer_class = SubmittedAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Если пользователь - учитель, показываем все отправленные задания
            return SubmittedAssignment.objects.all()
        elif hasattr(user, 'student'):
            # Если пользователь - студент, показываем только его задания
            return SubmittedAssignment.objects.filter(Student=user)
        return SubmittedAssignment.objects.none()

    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        submission = self.get_object()
        submission.grade = request.data.get('grade')
        submission.save()
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

class AssignmentManagementViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Учителя видят все задания
            return Assignment.objects.all()
        elif hasattr(user, 'student'):
            # Студенты видят только задания для своих предметов
            return Assignment.objects.filter(
                lesson__theme__subject__studentgroup__student=user.student
            )
        return Assignment.objects.none()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        submitted = SubmittedAssignment.objects.create(
            Assignment=assignment,
            Student=request.user,
            submittedassignment=request.data.get('file'),
            comment=request.data.get('comment', '')
        )
        serializer = SubmittedAssignmentSerializer(submitted)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        assignment = self.get_object()
        user = request.user
        
        if not hasattr(user, 'teacher'):
            return Response(
                {"error": "Only teachers can view submissions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submissions = SubmittedAssignment.objects.filter(Assignment=assignment)
        serializer = SubmittedAssignmentSerializer(submissions, many=True)
        return Response(serializer.data)



    @action(detail=True, methods=['post'])
    def grade_submission(self, request, pk=None):
        assignment = self.get_object()
        user = request.user
        
        if not hasattr(user, 'teacher'):
            return Response(
                {"error": "Only teachers can grade submissions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submission_id = request.data.get('submission_id')
        grade = request.data.get('grade')
        
        if not submission_id or not grade:
            return Response(
                {"error": "Submission ID and grade are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            submission = SubmittedAssignment.objects.get(
                id=submission_id,
                Assignment=assignment
            )
            submission.grade = grade
            submission.save()
            
            serializer = SubmittedAssignmentSerializer(submission)
            return Response(serializer.data)
        except SubmittedAssignment.DoesNotExist:
            return Response(
                {"error": "Submission not found"},
                status=status.HTTP_404_NOT_FOUND
            )