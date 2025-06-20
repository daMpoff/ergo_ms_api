from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Teacher, Student, StudentGroup, Subject, Grade, Theme,
    Lesson, TestBank, Test, Question, Answer, TestAttempt,
    StudentAnswer, StudentAnswerSelection, Assignment,
    SubmittedAssignment, UserRole, UserProfile, CourseCategory,
    Enrollment, CourseFile, Forum, ForumDiscussion, ForumPost,
    CalendarEvent, Badge, UserBadge, Notification, PrivateMessage
)

class LMSUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'date_joined']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

class UserRoleSerializer(serializers.ModelSerializer):
    user = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = UserRole
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    user = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'

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
    students_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentGroup
        fields = '__all__'
    
    def get_students_count(self, obj):
        return obj.student_set.count()

class CourseCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseCategory
        fields = '__all__'
    
    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_visible=True)
        return CourseCategorySerializer(subcategories, many=True).data
    
    def get_courses_count(self, obj):
        return obj.subject_set.filter(is_published=True).count()

class SubjectSerializer(serializers.ModelSerializer):
    teacher = LMSUserSerializer(read_only=True)
    category = CourseCategorySerializer(read_only=True)
    enrolled_students_count = serializers.SerializerMethodField()
    themes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = '__all__'
    
    def get_enrolled_students_count(self, obj):
        return obj.enrollment_set.filter(status='active').count()
    
    def get_themes_count(self, obj):
        return obj.theme_set.count()

class EnrollmentSerializer(serializers.ModelSerializer):
    student = LMSUserSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = '__all__'

class GradeSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    student = LMSUserSerializer(read_only=True)
    grader = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = Grade
        fields = '__all__'

class ThemeSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    lessons_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Theme
        fields = '__all__'
    
    def get_lessons_count(self, obj):
        return obj.lesson_set.count()

class CourseFileSerializer(serializers.ModelSerializer):
    uploaded_by = LMSUserSerializer(read_only=True)
    file_size_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseFile
        fields = '__all__'
    
    def get_file_size_formatted(self, obj):
        """Format file size in human readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

class LessonSerializer(serializers.ModelSerializer):
    theme = ThemeSerializer(read_only=True)
    files = CourseFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lesson
        fields = '__all__'

class ForumSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    created_by = LMSUserSerializer(read_only=True)
    discussions_count = serializers.SerializerMethodField()
    last_post = serializers.SerializerMethodField()
    
    class Meta:
        model = Forum
        fields = '__all__'
    
    def get_discussions_count(self, obj):
        return obj.discussions.count()
    
    def get_last_post(self, obj):
        last_discussion = obj.discussions.order_by('-last_post_at').first()
        if last_discussion:
            return {
                'discussion_name': last_discussion.name,
                'last_post_at': last_discussion.last_post_at,
                'posts_count': last_discussion.posts_count
            }
        return None

class ForumPostSerializer(serializers.ModelSerializer):
    author = LMSUserSerializer(read_only=True)
    attachments = CourseFileSerializer(many=True, read_only=True)
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumPost
        fields = '__all__'
    
    def get_replies_count(self, obj):
        return obj.replies.count()

class ForumDiscussionSerializer(serializers.ModelSerializer):
    forum = ForumSerializer(read_only=True)
    created_by = LMSUserSerializer(read_only=True)
    recent_posts = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumDiscussion
        fields = '__all__'
    
    def get_recent_posts(self, obj):
        recent_posts = obj.posts.order_by('-created_at')[:3]
        return ForumPostSerializer(recent_posts, many=True).data

class CalendarEventSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    created_by = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = '__all__'

class BadgeSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    awarded_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Badge
        fields = '__all__'
    
    def get_awarded_count(self, obj):
        return obj.userbadge_set.count()

class UserBadgeSerializer(serializers.ModelSerializer):
    user = LMSUserSerializer(read_only=True)
    badge = BadgeSerializer(read_only=True)
    awarded_by = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = UserBadge
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    recipient = LMSUserSerializer(read_only=True)
    sender = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'

class PrivateMessageSerializer(serializers.ModelSerializer):
    sender = LMSUserSerializer(read_only=True)
    recipient = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = PrivateMessage
        fields = '__all__'

class TestBankSerializer(serializers.ModelSerializer):
    created_by = LMSUserSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TestBank
        fields = '__all__'
    
    def get_questions_count(self, obj):
        return obj.questions.count()

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
    attempts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Test
        fields = '__all__'
    
    def get_attempts_count(self, obj):
        return obj.attempts.count()

class StudentAnswerSelectionSerializer(serializers.ModelSerializer):
    answer = AnswerSerializer(read_only=True)
    
    class Meta:
        model = StudentAnswerSelection
        fields = '__all__'

class StudentAnswerSerializer(serializers.ModelSerializer):
    selected_answers = StudentAnswerSelectionSerializer(many=True, read_only=True)
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = StudentAnswer
        fields = '__all__'

class TestAttemptSerializer(serializers.ModelSerializer):
    test = TestSerializer(read_only=True)
    student = LMSUserSerializer(read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True)
    score_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TestAttempt
        fields = '__all__'
    
    def get_score_percentage(self, obj):
        return obj.calculate_score()

class AssignmentSerializer(serializers.ModelSerializer):
    lesson = LessonSerializer(read_only=True)
    submissions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = '__all__'
    
    def get_submissions_count(self, obj):
        return obj.submittedassignment_set.count()

class SubmittedAssignmentSerializer(serializers.ModelSerializer):
    student = LMSUserSerializer(read_only=True)
    assignment = AssignmentSerializer(read_only=True)
    graded_by = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = SubmittedAssignment
        fields = '__all__'

# Специальные сериализаторы для создания и обновления
class CreateSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        exclude = ['teacher', 'creationdate', 'lastupdate']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)

class CreateForumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forum
        exclude = ['created_by', 'created_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class CreateAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        exclude = ['creationdate', 'lastupdate']

class StudentStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики студента"""
    average_grade = serializers.FloatField()
    total_tests = serializers.IntegerField()
    passed_tests = serializers.IntegerField()
    submitted_assignments = serializers.IntegerField()
    enrolled_courses = serializers.IntegerField()
    completed_courses = serializers.IntegerField()
    total_badges = serializers.IntegerField()
    forum_posts = serializers.IntegerField()

class TeacherStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики преподавателя"""
    total_students = serializers.IntegerField()
    total_subjects = serializers.IntegerField()
    average_grades = serializers.FloatField()
    active_tests = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    forum_discussions = serializers.IntegerField()
    badges_awarded = serializers.IntegerField()
