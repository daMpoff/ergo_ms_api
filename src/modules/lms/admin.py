from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    UserRole, UserProfile, Teacher, Student, StudentGroup,
    CourseCategory, CourseFormat, Subject, Enrollment, Grade, Theme, Lesson,
    CourseFile, Forum, ForumDiscussion, ForumPost,
    TestBank, Test, Question, Answer, TestAttempt,
    StudentAnswer, StudentAnswerSelection, Assignment,
    SubmittedAssignment, CalendarEvent, Badge, UserBadge,
    Notification, PrivateMessage
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'language', 'timezone', 'email_notifications', 'created_at']
    list_filter = ['language', 'timezone', 'email_notifications', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'avatar', 'bio')
        }),
        ('Настройки', {
            'fields': ('language', 'timezone', 'email_notifications')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'city', 'country', 'date_of_birth')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'academic_degree']
    search_fields = ['user__username', 'user__email', 'department']
    list_filter = ['department']


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'curator', 'specialization', 'year_of_study', 'students_count']
    list_filter = ['year_of_study', 'specialization']
    search_fields = ['name', 'specialization']
    
    def students_count(self, obj):
        return obj.student_set.count()
    students_count.short_description = 'Количество студентов'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'student_id', 'enrollment_date']
    list_filter = ['group', 'enrollment_date']
    search_fields = ['user__username', 'user__email', 'student_id']


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order', 'is_visible', 'courses_count']
    list_filter = ['is_visible', 'parent']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    
    def courses_count(self, obj):
        return obj.subject_set.count()
    courses_count.short_description = 'Количество курсов'


@admin.register(CourseFormat)
class CourseFormatAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'courses_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def courses_count(self, obj):
        return obj.subject_set.count()
    courses_count.short_description = 'Количество курсов'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher', 'category', 'course_format', 'is_published', 'enrolled_count']
    list_filter = ['is_published', 'course_format', 'category', 'creationdate']
    search_fields = ['name', 'description', 'teacher__username']
    date_hierarchy = 'creationdate'
    readonly_fields = ['creationdate', 'lastupdate']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'teacher', 'category')
        }),
        ('Настройки курса', {
            'fields': ('course_format', 'is_published', 'start_date', 'end_date')
        }),
        ('Запись на курс', {
            'fields': ('is_self_enrollment', 'enrollment_key', 'max_enrollment', 'guest_access')
        }),
        ('Дополнительно', {
            'fields': ('summary', 'course_image', 'completion_tracking'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('creationdate', 'lastupdate'),
            'classes': ('collapse',)
        }),
    )
    
    def enrolled_count(self, obj):
        return obj.enrollment_set.filter(status='active').count()
    enrolled_count.short_description = 'Записано студентов'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'status', 'progress_percentage', 'enrollment_date']
    list_filter = ['status', 'enrollment_date', 'subject']
    search_fields = ['student__username', 'subject__name']
    readonly_fields = ['enrollment_date', 'completion_date']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'grade', 'grade_type', 'grader', 'lastupdate']
    list_filter = ['grade_type', 'subject', 'lastupdate']
    search_fields = ['student__username', 'subject__name']
    readonly_fields = ['lastupdate']


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'sort_order', 'is_visible', 'lessons_count']
    list_filter = ['subject', 'is_visible']
    search_fields = ['name', 'description']
    ordering = ['subject', 'sort_order']
    
    def lessons_count(self, obj):
        return obj.lesson_set.count()
    lessons_count.short_description = 'Количество уроков'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['name', 'theme', 'lessontype', 'sort_order', 'is_visible']
    list_filter = ['lessontype', 'is_visible', 'theme__subject']
    search_fields = ['name', 'description']
    ordering = ['theme', 'sort_order']
    readonly_fields = ['creationdate', 'lastupdate']


@admin.register(CourseFile)
class CourseFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'lesson', 'file_type', 'file_size_formatted', 'download_count']
    list_filter = ['file_type', 'subject', 'uploaded_at']
    search_fields = ['name', 'description']
    readonly_fields = ['uploaded_at', 'file_size', 'download_count']
    
    def file_size_formatted(self, obj):
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_formatted.short_description = 'Размер файла'


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'forum_type', 'created_by', 'discussions_count']
    list_filter = ['forum_type', 'subject', 'is_locked']
    search_fields = ['name', 'description']
    
    def discussions_count(self, obj):
        return obj.discussions.count()
    discussions_count.short_description = 'Количество дискуссий'


@admin.register(ForumDiscussion)
class ForumDiscussionAdmin(admin.ModelAdmin):
    list_display = ['name', 'forum', 'created_by', 'posts_count', 'is_pinned', 'is_locked']
    list_filter = ['forum', 'is_pinned', 'is_locked', 'created_at']
    search_fields = ['name']
    readonly_fields = ['posts_count', 'last_post_at']


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ['discussion', 'author', 'created_at', 'has_parent']
    list_filter = ['discussion__forum', 'created_at']
    search_fields = ['content', 'author__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_parent(self, obj):
        return obj.parent is not None
    has_parent.boolean = True
    has_parent.short_description = 'Ответ'


@admin.register(TestBank)
class TestBankAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'created_by', 'questions_count', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['name', 'description']
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = 'Количество вопросов'


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'type', 'duration_minutes', 'passing_score', 'is_active']
    list_filter = ['type', 'is_active', 'lesson__theme__subject']
    search_fields = ['title', 'name', 'description']
    readonly_fields = ['creationdate', 'lastupdate']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'test', 'type', 'points', 'difficulty']
    list_filter = ['type', 'difficulty', 'test']
    search_fields = ['text']
    inlines = [AnswerInline]
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Текст вопроса'


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'test', 'attempt_number', 'score', 'is_passed', 'status', 'started_at']
    list_filter = ['is_passed', 'status', 'test']
    search_fields = ['student__username', 'test__title']
    readonly_fields = ['started_at', 'completed_at']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'deadline', 'max_grade', 'submissions_count']
    list_filter = ['deadline', 'lesson__theme__subject']
    search_fields = ['title', 'description']
    readonly_fields = ['creationdate', 'lastupdate']
    
    def submissions_count(self, obj):
        return obj.submittedassignment_set.count()
    submissions_count.short_description = 'Количество сдач'


@admin.register(SubmittedAssignment)
class SubmittedAssignmentAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'grade', 'dateofsubmit', 'graded_by']
    list_filter = ['assignment', 'dateofsubmit', 'graded_by']
    search_fields = ['assignment__title', 'student__username']
    readonly_fields = ['dateofsubmit', 'graded_at']


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'event_type', 'start_date', 'is_all_day']
    list_filter = ['event_type', 'subject', 'start_date', 'is_all_day']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_date'


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge_type', 'subject', 'is_active', 'awarded_count']
    list_filter = ['badge_type', 'is_active', 'subject']
    search_fields = ['name', 'description']
    
    def awarded_count(self, obj):
        return obj.userbadge_set.count()
    awarded_count.short_description = 'Количество награждений'


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'awarded_at', 'awarded_by']
    list_filter = ['badge', 'awarded_at', 'awarded_by']
    search_fields = ['user__username', 'badge__name']
    readonly_fields = ['awarded_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    readonly_fields = ['created_at']
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f'{count} уведомлений отмечено как прочитанные.')
    mark_as_read.short_description = 'Отметить как прочитанные'
    
    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f'{count} уведомлений отмечено как непрочитанные.')
    mark_as_unread.short_description = 'Отметить как непрочитанные'


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender', 'recipient', 'is_read', 'sent_at']
    list_filter = ['is_read', 'sent_at']
    search_fields = ['subject', 'content', 'sender__username', 'recipient__username']
    readonly_fields = ['sent_at', 'read_at']


# Настройка административного интерфейса
admin.site.site_header = 'LMS Администрирование'
admin.site.site_title = 'LMS Admin'
admin.site.index_title = 'Добро пожаловать в LMS' 