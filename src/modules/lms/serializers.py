from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models

from .models import (
    Teacher, Student, StudentGroup, Subject, Grade, Theme,
    Lesson, TestBank, Test, Question, Answer, TestAttempt,
    StudentAnswer, StudentAnswerSelection, Assignment,
    SubmittedAssignment, UserRole, UserProfile, CourseCategory,
    CourseFormat, Enrollment, CourseFile, Resource, Forum, ForumDiscussion, ForumPost,
    CalendarEvent, Badge, UserBadge, Notification, PrivateMessage,
    LessonItem
)
from .base_serializers import (
    LMSUserSerializer, BaseModelSerializer, TimestampedModelSerializer,
    CourseRelatedMixin, CountMixin
)
from .utils import format_file_size

class UserRoleSerializer(serializers.ModelSerializer):
    user = LMSUserSerializer(read_only=True)
    
    class Meta:
        model = UserRole
        fields = '__all__'

class LMSUserProfileSerializer(serializers.ModelSerializer):
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

class CourseCategorySerializer(BaseModelSerializer, CountMixin):
    subcategories = serializers.SerializerMethodField()
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseCategory
        fields = '__all__'
    
    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_visible=True)
        return CourseCategorySerializer(subcategories, many=True).data
    
    def get_courses_count(self, obj):
        return self.get_count_field(obj, 'subject_set', {'is_published': True})

class CourseFormatSerializer(BaseModelSerializer, CountMixin):
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseFormat
        fields = '__all__'
    
    def get_courses_count(self, obj):
        return self.get_count_field(obj, 'subject_set', {'is_published': True})

class SubjectSerializer(serializers.ModelSerializer):
    teacher = LMSUserSerializer(read_only=True)
    category = CourseCategorySerializer(read_only=True)
    course_format = CourseFormatSerializer(read_only=True)
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

class CreateEnrollmentSerializer(serializers.ModelSerializer):
    """Сериализатор для создания записи на курс"""
    
    class Meta:
        model = Enrollment
        fields = ['subject', 'enrollment_key']
    
    enrollment_key = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        subject = attrs.get('subject')
        enrollment_key = attrs.get('enrollment_key', '')
        
        # Проверяем, что пользователь еще не записан на курс
        if Enrollment.objects.filter(student=user, subject=subject).exists():
            raise serializers.ValidationError("Вы уже записаны на этот курс")
        
        # Проверяем ключ записи, если он требуется
        if subject.enrollment_key and enrollment_key != subject.enrollment_key:
            raise serializers.ValidationError("Неверный ключ записи")
        
        # Проверяем максимальное количество студентов
        if subject.max_enrollment:
            current_enrollments = Enrollment.objects.filter(
                subject=subject, status='active'
            ).count()
            if current_enrollments >= subject.max_enrollment:
                raise serializers.ValidationError("Превышено максимальное количество участников курса")
        
        return attrs
    
    def create(self, validated_data):
        # Удаляем enrollment_key из данных, он не нужен в модели
        validated_data.pop('enrollment_key', None)
        
        # Устанавливаем студента из запроса
        validated_data['student'] = self.context['request'].user
        validated_data['status'] = 'active'
        
        return super().create(validated_data)

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

class CourseFileSerializer(BaseModelSerializer):
    uploaded_by = LMSUserSerializer(read_only=True)
    file_size_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseFile
        fields = '__all__'
    
    def get_file_size_formatted(self, obj):
        """Format file size in human readable format"""
        return format_file_size(obj.file_size)

class LessonSerializer(serializers.ModelSerializer):
    theme = ThemeSerializer(read_only=True)
    files = CourseFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lesson
        fields = '__all__'

class ForumSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    theme = ThemeSerializer(read_only=True)
    lesson = LessonSerializer(read_only=True)
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
    subject = SubjectSerializer(read_only=True)
    theme = ThemeSerializer(read_only=True)
    lesson = LessonSerializer(read_only=True)
    test_bank = TestBankSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    attempts_count = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()

    def get_attempts_count(self, obj):
        return obj.attempts.count()
    
    def get_type_display(self, obj):
        """Возвращает читаемое название типа теста"""
        type_mapping = {
            'C': 'close',
            'O': 'open', 
            'G': 'game'
        }
        return type_mapping.get(obj.type, obj.type)
    
    def get_questions_count(self, obj):
        return obj.question_set.count()

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
    subject = SubjectSerializer(read_only=True)
    theme = ThemeSerializer(read_only=True)
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

class CreateSubmittedAssignmentSerializer(serializers.ModelSerializer):
    """Сериализатор для создания сданного задания"""
    
    class Meta:
        model = SubmittedAssignment
        fields = ['assignment', 'submission_text', 'file', 'comment']
    
    file = serializers.FileField(required=False, source='submittedassignment')
    
    def validate_assignment(self, value):
        """Проверяем что задание существует и доступно студенту"""
        user = self.context['request'].user
        
        # Проверяем что студент записан на курс, содержащий это задание
        enrolled_subjects = Enrollment.objects.filter(
            student=user, status='active'
        ).values_list('subject', flat=True)
        
        assignment_subjects = []
        if value.subject:
            assignment_subjects.append(value.subject.id)
        elif value.theme:
            assignment_subjects.append(value.theme.subject.id)
        elif value.lesson:
            assignment_subjects.append(value.lesson.theme.subject.id)
        
        if not any(subject_id in enrolled_subjects for subject_id in assignment_subjects):
            raise serializers.ValidationError("У вас нет доступа к этому заданию")
        
        # Проверяем что задание еще не сдано этим студентом
        if SubmittedAssignment.objects.filter(assignment=value, student=user).exists():
            raise serializers.ValidationError("Это задание уже было сдано")
        
        return value
    
    def validate(self, attrs):
        """Валидация данных формы"""
        assignment = attrs.get('assignment')
        submission_text = attrs.get('submission_text', '')
        file = attrs.get('submittedassignment')
        
        if not assignment:
            raise serializers.ValidationError({'assignment': 'Поле assignment обязательно'})
        
        # Проверяем что данные соответствуют типу сдачи задания
        if assignment.submission_type == 'file' and not file:
            raise serializers.ValidationError({'file': 'Для этого задания требуется загрузить файл'})
        elif assignment.submission_type == 'text' and not submission_text.strip():
            raise serializers.ValidationError({'submission_text': 'Для этого задания требуется текстовый ответ'})
        elif assignment.submission_type == 'both' and not file and not submission_text.strip():
            raise serializers.ValidationError('Для этого задания требуется файл или текстовый ответ')
        
        return attrs
    
    def create(self, validated_data):
        """Создание сданного задания с автоматической установкой студента"""
        validated_data['student'] = self.context['request'].user
        
        # Обрабатываем файл
        file_data = validated_data.pop('submittedassignment', None)
        if file_data:
            # Читаем файл в бинарном виде
            file_content = file_data.read()
            validated_data['submittedassignment'] = file_content
        
        return super().create(validated_data)

# Специальные сериализаторы для создания и обновления
class CreateTestSerializer(serializers.ModelSerializer):
    """Сериализатор для создания теста"""
    class Meta:
        model = Test
        exclude = ['creationdate', 'lastupdate']
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Название теста обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название теста должно содержать минимум 3 символа.")
        if len(value) > 100:
            raise serializers.ValidationError("Название теста не должно превышать 100 символов.")
        
        return value
    
    def validate_title(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError("Заголовок не должен превышать 255 символов.")
        return value or ''
    
    def validate_type(self, value):
        # Конвертируем значения фронтенда в значения модели
        type_mapping = {
            'close': 'C',
            'open': 'O', 
            'game': 'G'
        }
        
        if value in type_mapping:
            return type_mapping[value]
        elif value in ['C', 'O', 'G']:
            return value
        else:
            raise serializers.ValidationError("Неверный тип теста. Допустимые значения: close, open, game")
    
    def validate_duration_minutes(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Продолжительность теста должна быть больше 0 минут.")
        return value or 60
    
    def validate_passing_score(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Проходной балл должен быть от 0 до 100.")
        return value or 70
    
    def validate_max_attempts(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Максимальное количество попыток должно быть больше 0.")
        return value or 1
    
    def validate(self, attrs):
        # Валидация дат доступности
        available_from = attrs.get('available_from')
        available_until = attrs.get('available_until')
        
        errors = {}
        
        if available_from and available_until:
            if available_from >= available_until:
                errors['available_from'] = 'Дата начала должна быть раньше даты окончания.'
                errors['available_until'] = 'Дата окончания должна быть позже даты начала.'
        
        # Валидация принадлежности (тест должен принадлежать хотя бы одной сущности)
        subject = attrs.get('subject')
        theme = attrs.get('theme')
        lesson = attrs.get('lesson')
        
        if not any([subject, theme, lesson]):
            errors['general'] = 'Тест должен принадлежать курсу, теме или уроку'
        
        # Проверяем согласованность связей
        if lesson and theme:
            if lesson.theme_id != theme.id:
                errors['lesson'] = 'Урок должен принадлежать выбранной теме'
        
        if lesson and subject:
            if lesson.theme.subject_id != subject.id:
                errors['lesson'] = 'Урок должен принадлежать выбранному курсу'
        
        if theme and subject:
            if theme.subject_id != subject.id:
                errors['theme'] = 'Тема должна принадлежать выбранному курсу'
        
        # Проверяем права пользователя
        user = self.context['request'].user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles:
            # Определяем курс для проверки прав
            course_to_check = None
            if lesson:
                course_to_check = lesson.theme.subject
            elif theme:
                course_to_check = theme.subject
            elif subject:
                course_to_check = subject
            
            if course_to_check and course_to_check.teacher != user:
                errors['permissions'] = 'У вас нет прав на создание теста в этом курсе'
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return attrs
    
    def create(self, validated_data):
        # Устанавливаем значения по умолчанию
        validated_data.setdefault('title', validated_data.get('name', ''))
        validated_data.setdefault('description', '')
        validated_data.setdefault('duration_minutes', 60)
        validated_data.setdefault('passing_score', 70)
        validated_data.setdefault('max_attempts', 1)
        validated_data.setdefault('is_active', True)
        validated_data.setdefault('show_correct_answers', False)
        validated_data.setdefault('randomize_questions', False)
        validated_data.setdefault('sort_order', 0)
        
        return super().create(validated_data)

class UpdateTestSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления теста"""
    class Meta:
        model = Test
        exclude = ['creationdate']  # Не позволяем менять дату создания
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Название теста обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название теста должно содержать минимум 3 символа.")
        if len(value) > 100:
            raise serializers.ValidationError("Название теста не должно превышать 100 символов.")
        
        return value
    
    def validate_title(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError("Заголовок не должен превышать 255 символов.")
        return value or ''
    
    def validate_type(self, value):
        # Конвертируем значения фронтенда в значения модели
        type_mapping = {
            'close': 'C',
            'open': 'O', 
            'game': 'G'
        }
        
        if value in type_mapping:
            return type_mapping[value]
        elif value in ['C', 'O', 'G']:
            return value
        else:
            raise serializers.ValidationError("Неверный тип теста. Допустимые значения: close, open, game")
    
    def validate_duration_minutes(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Продолжительность теста должна быть больше 0 минут.")
        return value
    
    def validate_passing_score(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Проходной балл должен быть от 0 до 100.")
        return value
    
    def validate_max_attempts(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Максимальное количество попыток должно быть больше 0.")
        return value
    
    def validate_sort_order(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным.")
        return value or 0
    
    def validate(self, attrs):
        # Валидация дат доступности
        available_from = attrs.get('available_from')
        available_until = attrs.get('available_until')
        
        errors = {}
        
        if available_from and available_until:
            if available_from >= available_until:
                errors['available_from'] = 'Дата начала должна быть раньше даты окончания.'
                errors['available_until'] = 'Дата окончания должна быть позже даты начала.'
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return attrs
    
    def update(self, instance, validated_data):
        # Обновляем lastupdate автоматически
        validated_data['lastupdate'] = timezone.now()
        return super().update(instance, validated_data)

class CreateSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        exclude = ['teacher', 'creationdate', 'lastupdate']
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Название курса обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название курса должно содержать минимум 3 символа.")
        if len(value) > 100:
            raise serializers.ValidationError("Название курса не должно превышать 100 символов.")
        
        return value
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Описание курса обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Описание курса должно содержать минимум 10 символов.")
        
        return value
    
    def validate_summary(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError("Краткое описание не должно превышать 500 символов.")
        return value
    
    def validate_enrollment_key(self, value):
        if value and len(value) > 50:
            raise serializers.ValidationError("Ключ записи не должен превышать 50 символов.")
        return value
    
    def validate_max_enrollment(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Максимум студентов должен быть больше 0.")
        return value
    
    def validate(self, attrs):
        # Валидация дат
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        errors = {}
        
        if start_date and end_date:
            if start_date >= end_date:
                errors['start_date'] = 'Дата начала должна быть раньше даты окончания.'
                errors['end_date'] = 'Дата окончания должна быть позже даты начала.'
        elif start_date and not end_date:
            errors['end_date'] = 'Укажите дату окончания курса.'
        elif end_date and not start_date:
            errors['start_date'] = 'Укажите дату начала курса.'
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return attrs
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)

class UpdateSubjectSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления курса"""
    class Meta:
        model = Subject
        exclude = ['teacher', 'creationdate']  # Не позволяем менять автора и дату создания
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Название курса обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название курса должно содержать минимум 3 символа.")
        if len(value) > 100:
            raise serializers.ValidationError("Название курса не должно превышать 100 символов.")
        
        return value
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Описание курса обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Описание курса должно содержать минимум 10 символов.")
        
        return value
    
    def validate_summary(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError("Краткое описание не должно превышать 500 символов.")
        return value
    
    def validate_enrollment_key(self, value):
        if value and len(value) > 50:
            raise serializers.ValidationError("Ключ записи не должен превышать 50 символов.")
        return value
    
    def validate_max_enrollment(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Максимум студентов должен быть больше 0.")
        return value
    
    def validate(self, attrs):
        # Валидация дат
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        errors = {}
        
        if start_date and end_date:
            if start_date >= end_date:
                errors['start_date'] = 'Дата начала должна быть раньше даты окончания.'
                errors['end_date'] = 'Дата окончания должна быть позже даты начала.'
        elif start_date and not end_date:
            errors['end_date'] = 'Укажите дату окончания курса.'
        elif end_date and not start_date:
            errors['start_date'] = 'Укажите дату начала курса.'
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return attrs
    
    def update(self, instance, validated_data):
        # Обрабатываем удаление изображения
        if self.initial_data.get('remove_image') == 'true':
            if instance.course_image:
                # Удаляем файл изображения
                instance.course_image.delete(save=False)
            validated_data['course_image'] = None
        
        # Обновляем lastupdate автоматически
        validated_data['lastupdate'] = timezone.now()
        return super().update(instance, validated_data)

class CreateForumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forum
        exclude = ['created_by', 'created_at']
    
    def validate_sort_order(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным.")
        return value or 0
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data.setdefault('sort_order', 0)
        return super().create(validated_data)

class CreateAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        exclude = ['creationdate', 'lastupdate']
    
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Название задания обязательно для заполнения.")
        
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название задания должно содержать минимум 3 символа.")
        if len(value) > 255:
            raise serializers.ValidationError("Название задания не должно превышать 255 символов.")
        
        return value
    
    def validate_max_grade(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Максимальная оценка должна быть больше 0.")
        return value or 100
    
    def validate_max_file_size(self, value):
        if value is not None and value < 1024:  # Минимум 1KB
            raise serializers.ValidationError("Максимальный размер файла должен быть больше 1KB.")
        return value
    
    def validate_sort_order(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным.")
        return value or 0
    
    def validate(self, attrs):
        # Валидация даты крайнего срока
        deadline = attrs.get('deadline')
        if deadline:
            from django.utils import timezone
            if deadline < timezone.now().date():
                raise serializers.ValidationError({
                    'deadline': 'Дата крайнего срока не может быть в прошлом.'
                })
        
        # Валидация принадлежности (задание должно принадлежать хотя бы одной сущности)
        subject = attrs.get('subject')
        theme = attrs.get('theme')
        lesson = attrs.get('lesson')
        
        if not any([subject, theme, lesson]):
            raise serializers.ValidationError("Задание должно принадлежать курсу, теме или уроку")
        
        # Проверяем согласованность связей
        if lesson and theme:
            if lesson.theme_id != theme.id:
                raise serializers.ValidationError({
                    'lesson': 'Урок должен принадлежать выбранной теме'
                })
        
        if lesson and subject:
            if lesson.theme.subject_id != subject.id:
                raise serializers.ValidationError({
                    'lesson': 'Урок должен принадлежать выбранному курсу'
                })
        
        if theme and subject:
            if theme.subject_id != subject.id:
                raise serializers.ValidationError({
                    'theme': 'Тема должна принадлежать выбранному курсу'
                })
        
        # Проверяем права пользователя
        user = self.context['request'].user
        user_roles = user.roles.values_list('role', flat=True)
        
        if 'admin' not in user_roles:
            # Определяем курс для проверки прав
            course_to_check = None
            if lesson:
                course_to_check = lesson.theme.subject
            elif theme:
                course_to_check = theme.subject
            elif subject:
                course_to_check = subject
            
            if course_to_check and course_to_check.teacher != user:
                raise serializers.ValidationError("У вас нет прав на создание задания в этом курсе")
        
        return attrs

    def create(self, validated_data):
        # Устанавливаем значения по умолчанию
        validated_data.setdefault('max_grade', 100)
        validated_data.setdefault('allow_late_submissions', False)
        validated_data.setdefault('submission_type', 'file')
        validated_data.setdefault('max_file_size', 10485760)  # 10MB
        validated_data.setdefault('sort_order', 0)
        
        return Assignment.objects.create(**validated_data)

# Новые сериализаторы для управления уроками
class CreateLessonSerializer(serializers.ModelSerializer):
    """Сериализатор для создания урока"""
    
    class Meta:
        model = Lesson
        exclude = ['creationdate', 'lastupdate']
        
    def validate_name(self, value):
        """Валидация названия урока"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Название урока должно содержать минимум 3 символа")
        
        if len(value) > 100:
            raise serializers.ValidationError("Название урока не должно превышать 100 символов")
            
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания урока"""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Описание урока не должно превышать 1000 символов")
        return value
    
    def validate_sort_order(self, value):
        """Валидация порядка сортировки"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным")
        return value
    
    def validate(self, attrs):
        """Комплексная валидация"""
        theme = attrs.get('theme')
        name = attrs.get('name', '')
        
        # Проверяем уникальность названия урока в рамках темы
        if theme and name:
            existing_lesson = Lesson.objects.filter(
                theme=theme, 
                name__iexact=name.strip()
            ).first()
            
            if existing_lesson:
                raise serializers.ValidationError({
                    'name': f'Урок с названием "{name}" уже существует в этой теме'
                })
        
        # Валидация дат доступности
        availability_start = attrs.get('availability_start')
        availability_end = attrs.get('availability_end')
        
        if availability_start and availability_end:
            if availability_start >= availability_end:
                raise serializers.ValidationError({
                    'availability_end': 'Дата окончания должна быть позже даты начала'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Создание урока"""
        # Устанавливаем порядок сортировки автоматически если не указан
        if 'sort_order' not in validated_data or validated_data['sort_order'] is None:
            theme = validated_data['theme']
            max_order = Lesson.objects.filter(theme=theme).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            validated_data['sort_order'] = (max_order or 0) + 1
        
        return Lesson.objects.create(**validated_data)

class UpdateLessonSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления урока"""
    
    class Meta:
        model = Lesson
        exclude = ['creationdate']  # Не позволяем менять дату создания
        
    def validate_name(self, value):
        """Валидация названия урока"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Название урока должно содержать минимум 3 символа")
        
        if len(value) > 100:
            raise serializers.ValidationError("Название урока не должно превышать 100 символов")
            
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания урока"""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Описание урока не должно превышать 1000 символов")
        return value
    
    def validate_sort_order(self, value):
        """Валидация порядка сортировки"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным")
        return value
    
    def validate(self, attrs):
        """Комплексная валидация"""
        theme = attrs.get('theme')
        name = attrs.get('name', '')
        instance = self.instance
        
        # Проверяем уникальность названия урока в рамках темы (исключая текущий урок)
        if theme and name:
            existing_lesson = Lesson.objects.filter(
                theme=theme, 
                name__iexact=name.strip()
            ).exclude(id=instance.id if instance else None).first()
            
            if existing_lesson:
                raise serializers.ValidationError({
                    'name': f'Урок с названием "{name}" уже существует в этой теме'
                })
        
        # Валидация дат доступности
        availability_start = attrs.get('availability_start')
        availability_end = attrs.get('availability_end')
        
        if availability_start and availability_end:
            if availability_start >= availability_end:
                raise serializers.ValidationError({
                    'availability_end': 'Дата окончания должна быть позже даты начала'
                })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Обновление урока"""
        # Обновляем lastupdate автоматически
        validated_data['lastupdate'] = timezone.now()
        
        # Обновляем поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class CreateThemeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания темы курса"""
    
    # Делаем поле description необязательным
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Theme
        exclude = ['creationdate', 'lastupdate']
        
    def validate_name(self, value):
        """Валидация названия темы"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Название темы должно содержать минимум 3 символа")
        
        if len(value) > 100:
            raise serializers.ValidationError("Название темы не должно превышать 100 символов")
            
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания темы - необязательное поле"""
        # Описание полностью необязательно
        if value is None or value == '' or (isinstance(value, str) and not value.strip()):
            return ''
        
        # Приводим к строке и убираем лишние пробелы
        value = str(value).strip()
        
        if len(value) > 1000:
            raise serializers.ValidationError("Описание темы не должно превышать 1000 символов")
        return value
    
    def validate_sort_order(self, value):
        """Валидация порядка сортировки"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным")
        return value
    
    def validate(self, attrs):
        """Комплексная валидация"""
        subject = attrs.get('subject')
        name = attrs.get('name', '')
        
        # Проверяем уникальность названия темы в рамках курса
        if subject and name:
            existing_theme = Theme.objects.filter(
                subject=subject, 
                name__iexact=name.strip()
            ).first()
            
            if existing_theme:
                raise serializers.ValidationError({
                    'name': f'Тема с названием "{name}" уже существует в этом курсе'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Создание темы"""
        # Устанавливаем порядок сортировки автоматически если не указан
        if 'sort_order' not in validated_data or validated_data['sort_order'] is None:
            subject = validated_data['subject']
            max_order = Theme.objects.filter(subject=subject).aggregate(
                max_order=models.Max('sort_order')
            )['max_order']
            validated_data['sort_order'] = (max_order or 0) + 1
        
        return Theme.objects.create(**validated_data)

class UpdateThemeSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления темы курса"""
    
    # Делаем поле description необязательным
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Theme
        exclude = ['creationdate', 'sort_order']  # Не позволяем менять дату создания и порядок сортировки
        
    def validate_name(self, value):
        """Валидация названия темы"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Название темы должно содержать минимум 3 символа")
        
        if len(value) > 100:
            raise serializers.ValidationError("Название темы не должно превышать 100 символов")
            
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания темы - необязательное поле"""
        # Описание полностью необязательно
        if value is None or value == '' or (isinstance(value, str) and not value.strip()):
            return ''
        
        # Приводим к строке и убираем лишние пробелы
        value = str(value).strip()
        
        if len(value) > 1000:
            raise serializers.ValidationError("Описание темы не должно превышать 1000 символов")
        return value
    
    def validate(self, attrs):
        """Комплексная валидация"""
        subject = attrs.get('subject')
        name = attrs.get('name', '')
        instance = self.instance
        
        # Проверяем уникальность названия темы в рамках курса (исключая текущую тему)
        if subject and name:
            existing_theme = Theme.objects.filter(
                subject=subject, 
                name__iexact=name.strip()
            ).exclude(id=instance.id if instance else None).first()
            
            if existing_theme:
                raise serializers.ValidationError({
                    'name': f'Тема с названием "{name}" уже существует в этом курсе'
                })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Обновление темы"""
        # Обновляем lastupdate автоматически
        validated_data['lastupdate'] = timezone.now()
        
        # Обновляем поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

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

class ResourceSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра ресурсов"""
    uploaded_by = LMSUserSerializer(read_only=True)
    file_size_formatted = serializers.SerializerMethodField()
    subject = SubjectSerializer(read_only=True)
    theme = ThemeSerializer(read_only=True)
    lesson = LessonSerializer(read_only=True)
    
    class Meta:
        model = Resource
        fields = '__all__'
    
    def get_file_size_formatted(self, obj):
        """Форматирование размера файла"""
        if not obj.file_size:
            return "0 байт"
            
        for unit in ['байт', 'КБ', 'МБ', 'ГБ']:
            if obj.file_size < 1024.0:
                return f"{obj.file_size:.1f} {unit}"
            obj.file_size /= 1024.0
        return f"{obj.file_size:.1f} ТБ"

class CreateResourceSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ресурса"""
    file = serializers.FileField(required=True)
    
    class Meta:
        model = Resource
        exclude = ['uploaded_at', 'uploaded_by', 'file_size', 'file_type', 'download_count']
    
    def validate_name(self, value):
        """Валидация названия ресурса"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Название ресурса должно содержать минимум 2 символа")
        
        if len(value) > 255:
            raise serializers.ValidationError("Название ресурса не должно превышать 255 символов")
            
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания ресурса"""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Описание ресурса не должно превышать 1000 символов")
        return value
    
    def validate_file(self, value):
        """Валидация файла"""
        if not value:
            raise serializers.ValidationError("Файл обязателен")
        
        # Проверяем размер файла (максимум 100 МБ)
        max_size = 100 * 1024 * 1024  # 100 МБ в байтах
        if value.size > max_size:
            raise serializers.ValidationError("Размер файла не должен превышать 100 МБ")
        
        return value
    
    def validate_sort_order(self, value):
        """Валидация порядка сортировки"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок сортировки не может быть отрицательным")
        return value or 0
    
    def validate(self, attrs):
        """Комплексная валидация"""
        subject = attrs.get('subject')
        theme = attrs.get('theme')
        lesson = attrs.get('lesson')
        
        # Ресурс должен принадлежать хотя бы одной из сущностей
        if not any([subject, theme, lesson]):
            raise serializers.ValidationError("Ресурс должен принадлежать курсу, теме или уроку")
        
        # Ресурс не может принадлежать одновременно уроку и теме/курсу если урок не принадлежит этой теме/курсу
        if lesson and theme:
            if lesson.theme_id != theme.id:
                raise serializers.ValidationError("Урок должен принадлежать выбранной теме")
        
        if lesson and subject:
            if lesson.theme.subject_id != subject.id:
                raise serializers.ValidationError("Урок должен принадлежать выбранному курсу")
        
        if theme and subject:
            if theme.subject_id != subject.id:
                raise serializers.ValidationError("Тема должна принадлежать выбранному курсу")
        
        return attrs
    
    def create(self, validated_data):
        """Создание ресурса"""
        # Получаем информацию о файле
        file = validated_data['file']
        validated_data['file_size'] = file.size
        validated_data['file_type'] = file.content_type or 'application/octet-stream'
        
        # Устанавливаем порядок сортировки автоматически если не указан
        if 'sort_order' not in validated_data or validated_data['sort_order'] is None:
            # Определяем контекст для сортировки
            if validated_data.get('lesson'):
                max_order = Resource.objects.filter(lesson=validated_data['lesson']).aggregate(
                    max_order=models.Max('sort_order')
                )['max_order']
            elif validated_data.get('theme'):
                max_order = Resource.objects.filter(theme=validated_data['theme']).aggregate(
                    max_order=models.Max('sort_order')
                )['max_order']
            else:
                max_order = Resource.objects.filter(subject=validated_data['subject']).aggregate(
                    max_order=models.Max('sort_order')
                )['max_order']
            
            validated_data['sort_order'] = (max_order or 0) + 1
        
        # Устанавливаем значение по умолчанию как fallback
        validated_data.setdefault('sort_order', 0)
        validated_data['uploaded_by'] = self.context['request'].user
        
        return Resource.objects.create(**validated_data)

class UpdateResourceSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления ресурса"""
    file = serializers.FileField(required=False)
    
    class Meta:
        model = Resource
        exclude = ['uploaded_at', 'uploaded_by', 'download_count']
    
    def validate_name(self, value):
        """Валидация названия ресурса"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Название ресурса должно содержать минимум 2 символа")
        
        if len(value) > 255:
            raise serializers.ValidationError("Название ресурса не должно превышать 255 символов")
            
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания ресурса"""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Описание ресурса не должно превышать 1000 символов")
        return value
    
    def validate_file(self, value):
        """Валидация файла"""
        if value:
            # Проверяем размер файла (максимум 100 МБ)
            max_size = 100 * 1024 * 1024  # 100 МБ в байтах
            if value.size > max_size:
                raise serializers.ValidationError("Размер файла не должен превышать 100 МБ")
        
        return value
    
    def update(self, instance, validated_data):
        """Обновление ресурса"""
        # Если загружается новый файл, обновляем метаданные
        if 'file' in validated_data and validated_data['file']:
            file = validated_data['file']
            validated_data['file_size'] = file.size
            validated_data['file_type'] = file.content_type or 'application/octet-stream'
        
        # Обновляем поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class CreateQuestionSerializer(serializers.ModelSerializer):
    """Сериализатор для создания вопроса"""
    answers = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    
    class Meta:
        model = Question
        exclude = ['lastupdate']
    
    def validate_text(self, value):
        """Валидация текста вопроса"""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError("Текст вопроса должен содержать минимум 5 символов")
        
        if len(value) > 2000:
            raise serializers.ValidationError("Текст вопроса не должен превышать 2000 символов")
            
        return value.strip()
    
    def validate_points(self, value):
        """Валидация баллов"""
        if value < 1 or value > 100:
            raise serializers.ValidationError("Количество баллов должно быть от 1 до 100")
        return value
    
    def validate_type(self, value):
        """Валидация типа вопроса"""
        if value not in ['S', 'M', 'O', 'TF', 'MATCH']:
            raise serializers.ValidationError("Недопустимый тип вопроса")
        return value
    
    def validate(self, attrs):
        """Комплексная валидация"""
        question_type = attrs.get('type')
        answers = attrs.get('answers', [])
        
        # Для закрытых вопросов требуются варианты ответов
        if question_type in ['S', 'M', 'TF'] and not answers:
            raise serializers.ValidationError({
                'answers': 'Для закрытых вопросов требуются варианты ответов'
            })
        
        # Для одиночного выбора должен быть ровно один правильный ответ
        if question_type == 'S':
            correct_count = sum(1 for ans in answers if ans.get('is_correct'))
            if correct_count != 1:
                raise serializers.ValidationError({
                    'answers': 'Для вопроса с одним ответом должен быть выбран ровно один правильный вариант'
                })
        
        # Для множественного выбора должен быть хотя бы один правильный ответ
        if question_type == 'M':
            correct_count = sum(1 for ans in answers if ans.get('is_correct'))
            if correct_count < 1:
                raise serializers.ValidationError({
                    'answers': 'Для вопроса с множественным выбором должен быть выбран хотя бы один правильный вариант'
                })
        
        # Для True/False должно быть ровно 2 варианта
        if question_type == 'TF':
            if len(answers) != 2:
                raise serializers.ValidationError({
                    'answers': 'Для вопроса Верно/Неверно должно быть ровно 2 варианта ответа'
                })
            correct_count = sum(1 for ans in answers if ans.get('is_correct'))
            if correct_count != 1:
                raise serializers.ValidationError({
                    'answers': 'Для вопроса Верно/Неверно должен быть выбран ровно один правильный вариант'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Создание вопроса с ответами"""
        answers_data = validated_data.pop('answers', [])
        
        # Автоматически устанавливаем lastupdate
        validated_data['lastupdate'] = timezone.now()
        
        question = Question.objects.create(**validated_data)
        
        # Создаем варианты ответов
        for answer_data in answers_data:
            Answer.objects.create(
                question=question,
                text=answer_data.get('text', ''),
                is_correct=answer_data.get('is_correct', False)
            )
        
        return question

class CreateAnswerSerializer(serializers.ModelSerializer):
    """Сериализатор для создания варианта ответа"""
    
    class Meta:
        model = Answer
        exclude = ['created_at', 'updated_at']
    
    def validate_text(self, value):
        """Валидация текста ответа"""
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("Текст ответа не может быть пустым")
        
        if len(value) > 500:
            raise serializers.ValidationError("Текст ответа не должен превышать 500 символов")
            
        return value.strip()

# Сериализатор для изменения порядка элементов урока
class LessonItemReorderSerializer(serializers.Serializer):
    """Сериализатор для изменения порядка элементов урока"""
    lesson_id = serializers.IntegerField()
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        help_text="Список элементов в формате [{'id': item_id, 'sort_order': order}, ...]"
    )
    
    def validate_lesson_id(self, value):
        """Валидация ID урока"""
        try:
            from .models import Lesson
            lesson = Lesson.objects.get(id=value)
            return value
        except Lesson.DoesNotExist:
            raise serializers.ValidationError("Урок не найден")
    
    def validate_items(self, value):
        """Валидация элементов"""
        if not value:
            raise serializers.ValidationError("Список элементов не может быть пустым")
        
        item_ids = []
        for item in value:
            if 'id' not in item or 'sort_order' not in item:
                raise serializers.ValidationError("Каждый элемент должен содержать 'id' и 'sort_order'")
            
            item_id = item['id']
            if item_id in item_ids:
                raise serializers.ValidationError(f"Дублирующийся ID элемента: {item_id}")
            item_ids.append(item_id)
            
            if item['sort_order'] < 0:
                raise serializers.ValidationError("Порядок сортировки не может быть отрицательным")
        
        return value
    
    def save(self):
        """Обновляет порядок элементов урока"""
        from .models import LessonItem
        lesson_id = self.validated_data['lesson_id']
        items = self.validated_data['items']
        
        # Получаем все элементы урока для валидации
        lesson_items = LessonItem.objects.filter(lesson_id=lesson_id)
        existing_ids = set(lesson_items.values_list('id', flat=True))
        
        # Проверяем, что все переданные ID существуют и принадлежат этому уроку
        for item in items:
            if item['id'] not in existing_ids:
                raise serializers.ValidationError(f"Элемент с ID {item['id']} не найден в данном уроке")
        
        # Обновляем порядок
        for item in items:
            LessonItem.objects.filter(id=item['id']).update(sort_order=item['sort_order'])
        
        return lesson_items.order_by('sort_order')

# Сериализаторы для унифицированного управления элементами урока
class LessonItemSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра элементов урока"""
    content = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LessonItem
        fields = '__all__'
    
    def get_content(self, obj):
        """Возвращает данные связанного объекта"""
        content = obj.get_content_object()
        if not content:
            return None
        
        if obj.item_type == 'test':
            return TestSerializer(content).data
        elif obj.item_type == 'assignment':
            return AssignmentSerializer(content).data
        elif obj.item_type == 'resource':
            return ResourceSerializer(content).data
        return None
    
    def get_display_name(self, obj):
        """Возвращает отображаемое имя элемента"""
        return obj.get_display_name()
