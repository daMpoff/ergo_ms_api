from django.contrib import admin
from .models import (
    DevelopmentProgram, ProgramTopic, StrategicProject,
    ProjectStage, StageExecutor, ProjectReport,
    StageResult, ProjectHistory, UserProjectRole, EmployeeWorkload
)


@admin.register(DevelopmentProgram)
class DevelopmentProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'is_active', 'created_at', 'updated_at']
    list_filter = ['year', 'is_active']
    search_fields = ['name']
    ordering = ['-year', '-created_at']


@admin.register(ProgramTopic)
class ProgramTopicAdmin(admin.ModelAdmin):
    list_display = ['direction_code', 'topic_number', 'name', 'status', 'program']
    list_filter = ['status', 'program']
    search_fields = ['name', 'direction_code', 'topic_number']
    raw_id_fields = ['project']


@admin.register(StrategicProject)
class StrategicProjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'status', 'leader', 'created_at']
    list_filter = ['status', 'requires_budget', 'created_at']
    search_fields = ['code', 'name']
    raw_id_fields = ['topic', 'leader', 'curator', 'customer']
    readonly_fields = ['code', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('topic', 'code', 'name', 'status', 'rejection_comment')
        }),
        ('Участники', {
            'fields': ('leader', 'curator', 'customer')
        }),
        ('Описание', {
            'fields': ('goal', 'tasks', 'planned_results')
        }),
        ('Сроки и бюджет', {
            'fields': (
                ('planned_start_date', 'planned_end_date'),
                ('actual_start_date', 'actual_end_date'),
                'requires_budget', 'total_budget'
            )
        }),
        ('Служебная информация', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'order_number', 'status', 'planned_start_date', 'planned_end_date']
    list_filter = ['status', 'project']
    search_fields = ['name', 'project__name']
    ordering = ['project', 'order_number']


@admin.register(StageExecutor)
class StageExecutorAdmin(admin.ModelAdmin):
    list_display = ['user', 'stage', 'role', 'assigned_date']
    list_filter = ['role']
    raw_id_fields = ['user', 'stage']


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ['project', 'report_type', 'approval_status', 'created_at']
    list_filter = ['report_type', 'approval_status', 'created_at']
    search_fields = ['project__name', 'project__code']
    raw_id_fields = ['project', 'stage']


@admin.register(StageResult)
class StageResultAdmin(admin.ModelAdmin):
    list_display = ['stage', 'result_type', 'added_date']
    list_filter = ['result_type', 'added_date']
    search_fields = ['description']
    raw_id_fields = ['stage']


@admin.register(ProjectHistory)
class ProjectHistoryAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['project__name', 'project__code', 'action', 'description']
    raw_id_fields = ['project', 'user']
    readonly_fields = ['created_at']


@admin.register(UserProjectRole)
class UserProjectRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at', 'created_by']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user', 'created_by']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'role')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(EmployeeWorkload)
class EmployeeWorkloadAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'role_in_project', 'workload_percentage', 'start_date', 'end_date']
    list_filter = ['workload_percentage', 'start_date', 'end_date']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'project__name', 'project__code']
    raw_id_fields = ['user', 'project']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'project', 'role_in_project')
        }),
        ('Загруженность', {
            'fields': ('workload_percentage', 'start_date', 'end_date')
        })
    ) 