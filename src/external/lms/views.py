from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg
from .models import (
    Student, Teacher, StudentGroup, Subject,
    Test, TestAttempt, SubmittedAssignment
)

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    @action(detail=False, methods=['get'])
    def student_stats(self, request):
        student = Student.objects.get(user=request.user)
        grades = student.user.grade_set.all()
        
        stats = {
            'average_grade': grades.aggregate(Avg('grade'))['grade__avg'] or 0,
            'total_tests': TestAttempt.objects.filter(student=request.user).count(),
            'passed_tests': TestAttempt.objects.filter(
                student=request.user,
                is_passed=True
            ).count(),
            'submitted_assignments': SubmittedAssignment.objects.filter(
                Student=request.user
            ).count()
        }
        return Response(stats)

    @action(detail=False, methods=['get'])
    def teacher_stats(self, request):
        teacher = Teacher.objects.get(user=request.user)
        subjects = Subject.objects.filter(teacher=request.user)
        
        stats = {
            'total_students': Student.objects.filter(
                group__in=StudentGroup.objects.filter(curator=teacher)
            ).count(),
            'total_subjects': subjects.count(),
            'average_grades': subjects.aggregate(Avg('grade__grade'))['grade__grade__avg'] or 0,
            'active_tests': Test.objects.filter(
                lesson__theme__subject__in=subjects,
                is_active=True
            ).count()
        }
        return Response(stats)
