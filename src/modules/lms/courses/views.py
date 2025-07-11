from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from ..models import (
    Subject, Theme, Lesson, Student, Teacher,
    Grade, Test, Assignment
)
from ..serializers import (
    SubjectSerializer, ThemeSerializer, LessonSerializer,
    GradeSerializer
)

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            # Students can see subjects they are enrolled in
            return Subject.objects.filter(
                grade__student=user.student
            )
        elif hasattr(user, 'teacher'):
            # Teachers can see subjects they teach
            return Subject.objects.filter(teacher=user)
        return Subject.objects.none()

    @action(detail=True, methods=['get'])
    def themes(self, request, pk=None):
        subject = self.get_object()
        themes = Theme.objects.filter(subject=subject)
        serializer = ThemeSerializer(themes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        subject = self.get_object()
        user = request.user
        
        if hasattr(user, 'student'):
            # Students can see their own grades
            grades = Grade.objects.filter(
                subject=subject,
                student=user
            )
        elif hasattr(user, 'teacher'):
            # Teachers can see all grades for their subject
            grades = Grade.objects.filter(subject=subject)
        else:
            grades = Grade.objects.none()
            
        serializer = GradeSerializer(grades, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        subject = self.get_object()
        user = request.user
        
        if not hasattr(user, 'teacher'):
            return Response(
                {"error": "Only teachers can publish subjects"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        subject.is_published = True
        subject.save()
        serializer = SubjectSerializer(subject)
        return Response(serializer.data)

class ThemeViewSet(viewsets.ModelViewSet):
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            # Students can see themes for their subjects
            return Theme.objects.filter(
                subject__grade__student=user.student,
                subject__is_published=True
            )
        elif hasattr(user, 'teacher'):
            # Teachers can see themes for their subjects
            return Theme.objects.filter(subject__teacher=user)
        return Theme.objects.none()

    @action(detail=True, methods=['get'])
    def lessons(self, request, pk=None):
        theme = self.get_object()
        lessons = Lesson.objects.filter(theme=theme)
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            # Students can see lessons for their subjects
            return Lesson.objects.filter(
                theme__subject__grade__student=user.student,
                theme__subject__is_published=True
            )
        elif hasattr(user, 'teacher'):
            # Teachers can see lessons for their subjects
            return Lesson.objects.filter(theme__subject__teacher=user)
        return Lesson.objects.none()

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        lesson = self.get_object()
        return Response({
            'content': lesson.content,
            'type': lesson.lessontype
        })

    @action(detail=True, methods=['get'])
    def tests(self, request, pk=None):
        lesson = self.get_object()
        tests = Test.objects.filter(lesson=lesson)
        return Response({
            'tests': [
                {
                    'id': test.id,
                    'name': test.name,
                    'type': test.type,
                    'duration_minutes': test.duration_minutes,
                    'is_active': test.is_active
                }
                for test in tests
            ]
        })

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        lesson = self.get_object()
        assignments = Assignment.objects.filter(lesson=lesson)
        return Response({
            'assignments': [
                {
                    'id': assignment.id,
                    'title': assignment.title,
                    'deadline': assignment.deadline,
                    'description': assignment.description
                }
                for assignment in assignments
            ]
        })
