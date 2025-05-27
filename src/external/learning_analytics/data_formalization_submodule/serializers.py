# Импорт необходимых классов и модулей из Django REST Framework
from rest_framework import serializers

# Импорт модели Technology из приложения learning_analytics
from src.external.learning_analytics.data_formalization_submodule.models import (
    Speciality,                 # Модель специальностей
    Curriculum,                 # Модель учебного плана
    Technology,                 # Модель технологий
    Competency,                 # Модель компетенций
    BaseDiscipline,             # Модель базовых дисциплин
    Discipline,                 # Модель дисциплин
    Vacancy,                    # Модель вакансий
    ACM,                        # Модель матрицы академических компетенций
    VCM,                        # Модель профиля компетенций вакансии
    UCM,                        # Модель матрицы компетенций пользователя

    ImportHistory,             # Модель истории импорта
    ImportStats,               # Модель статистики импорта
)

class ImportHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportHistory
        fields = ['id', 'timestamp', 'data_type', 'file_name', 'records_count', 'status']

class ImportHistoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportHistory
        fields = ['id', 'timestamp', 'data_type', 'file_name', 'records_count', 'status']

class ImportStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportStats
        fields = ['id', 'sum_of_imported_files', 'sum_of_imported_records', 'last_file_timestamp']

class SpecialitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Speciality
        fields = ['id', 'code', 'name', 'specialization', 'department', 'faculty']

class CurriculumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curriculum
        fields = ['id', 'speciality', 'education_duration', 'year_of_admission', 'is_active']

class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = ['id', 'name', 'description', 'popularity', 'rating']

class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = [
            'id', 'code', 'name', 'description',
            'know_level', 'can_level', 'master_level',
            'blooms_level', 'blooms_verbs',
            'complexity', 'demand'
        ]

class BaseDisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseDiscipline
        fields = ['id', 'code', 'name', 'description']

class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        fields = [
            'id', 'curriculum', 'base_discipline', 
            'code', 'name', 'semesters',
            'contact_work_hours', 'independent_work_hours', 'control_work_hours',
            'technologies', 'competencies'
        ]

class VacancySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vacancy
        fields = [
            'id', 'employer', 'title', 'description',
            'requirements', 'responsibilities',
            'created_at', 'updated_at',
            'salary_min', 'salary_max',
            'is_active', 'location',
            'employment_type',
            'technologies', 'competencies'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ACMSerializer(serializers.ModelSerializer):
    class Meta:
        model = ACM
        fields = ['id', 'curriculum', 'discipline_list', 'technology_stack']

class VCMSerializer(serializers.ModelSerializer):
    class Meta:
        model = VCM
        fields = ['id', 'vacancy', 'technologies', 'competencies', 'description']

class UCMSerializer(serializers.ModelSerializer):
    class Meta:
        model = UCM 
        fields = ['id', 'user_id', 'competencies_stack', 'technology_stack']

