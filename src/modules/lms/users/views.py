from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from ..models import Teacher, Student, StudentGroup
from ..serializers import (
    LMSUserSerializer, TeacherSerializer, StudentSerializer,
    StudentGroupSerializer
)
from django.db.models import Q


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = LMSUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Teachers can see students in their groups
            return User.objects.filter(
                student__group__curator=user.teacher
            )
        elif hasattr(user, 'student'):
            # Students can see teachers and other students in their group
            return User.objects.filter(
                Q(teacher__studentgroup__student=user.student) |
                Q(student__group=user.student.group)
            )
        return User.objects.none()

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Teachers can see other teachers
            return Teacher.objects.all()
        elif hasattr(user, 'student'):
            # Students can see their teachers
            return Teacher.objects.filter(
                studentgroup__student=user.student
            )
        return Teacher.objects.none()

    @action(detail=True, methods=['get'])
    def student_groups(self, request, pk=None):
        teacher = self.get_object()
        groups = StudentGroup.objects.filter(curator=teacher)
        serializer = StudentGroupSerializer(groups, many=True)
        return Response(serializer.data)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Teachers can see students in their groups
            return Student.objects.filter(
                group__curator=user.teacher
            )
        elif hasattr(user, 'student'):
            # Students can see other students in their group
            return Student.objects.filter(
                group=user.student.group
            )
        return Student.objects.none()

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        student = self.get_object()
        grades = student.user.grade_set.all()
        return Response({
            'grades': [
                {
                    'subject': grade.subject.name,
                    'grade': grade.grade,
                    'date': grade.related
                }
                for grade in grades
            ]
        })

class StudentGroupViewSet(viewsets.ModelViewSet):
    queryset = StudentGroup.objects.all()
    serializer_class = StudentGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            # Teachers can see their groups
            return StudentGroup.objects.filter(curator=user.teacher)
        elif hasattr(user, 'student'):
            # Students can see their group
            return StudentGroup.objects.filter(student=user.student)
        return StudentGroup.objects.none()

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        group = self.get_object()
        students = Student.objects.filter(group=group)
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        group = self.get_object()
        user = request.user
        
        if not hasattr(user, 'teacher'):
            return Response(
                {"error": "Only teachers can add students to groups"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        if not student_id:
            return Response(
                {"error": "Student ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id)
            student.group = group
            student.save()
            serializer = StudentSerializer(student)
            return Response(serializer.data)
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )