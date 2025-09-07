from rest_framework import serializers
from .models import ImpulsAnalysis, ImpulsFile, ImpulsProtocol


class ImpulsFileSerializer(serializers.ModelSerializer):
    """Сериализатор для файлов анализа импульса"""
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = ImpulsFile
        fields = [
            'id', 'file_type', 'file_type_display', 'original_filename',
            'file', 'file_size', 'file_size_mb', 'uploaded_at'
        ]
        read_only_fields = ['id', 'file_size', 'file_size_mb', 'uploaded_at']
    
    def get_file_size_mb(self, obj):
        """Возвращает размер файла в МБ"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0


class ImpulsProtocolSerializer(serializers.ModelSerializer):
    """Сериализатор для протоколов анализа импульса"""
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = ImpulsProtocol
        fields = [
            'id', 'protocol_file', 'generated_at', 'file_size', 'file_size_mb'
        ]
        read_only_fields = ['id', 'generated_at', 'file_size', 'file_size_mb']
    
    def get_file_size_mb(self, obj):
        """Возвращает размер файла в МБ"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0


class ImpulsAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для анализа импульса"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    files = ImpulsFileSerializer(many=True, read_only=True)
    protocols = ImpulsProtocolSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = ImpulsAnalysis
        fields = [
            'id', 'title', 'description',
            'status', 'status_display', 'task_id', 'error_message',
            'files', 'protocols', 'user_email', 'created_at', 'updated_at',
            'started_at', 'completed_at', 'protocol_number', 'p_static', 'energy_j'
        ]
        read_only_fields = [
            'id', 'status', 'task_id', 'error_message',
            'files', 'protocols', 'user_email', 'created_at', 'updated_at',
            'started_at', 'completed_at', 'protocol_number', 'p_static', 'energy_j'
        ]


class ImpulsAnalysisCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания анализа импульса"""
    
    class Meta:
        model = ImpulsAnalysis
        fields = ['title', 'description']
        read_only_fields = ['id', 'status', 'task_id', 'error_message', 
                           'files', 'protocols', 'user_email', 'created_at', 'updated_at',
                           'started_at', 'completed_at', 'protocol_number', 'p_static', 'energy_j']


class ImpulsAnalysisUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления анализа импульса"""
    
    class Meta:
        model = ImpulsAnalysis
        fields = ['title', 'description']
        read_only_fields = ['id', 'status', 'task_id', 'error_message', 
                           'files', 'protocols', 'user_email', 'created_at', 'updated_at',
                           'started_at', 'completed_at', 'protocol_number', 'p_static', 'energy_j']


class ImpulsFileUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки файлов"""
    force_calculation_file = serializers.FileField(
        required=False,
        help_text="Excel файл с расчетом силы"
    )
    experiment_plan_file = serializers.FileField(
        required=False,
        help_text="Excel файл с планом эксперимента"
    )
    
    def validate(self, attrs):
        """Проверяем, что загружен хотя бы один файл"""
        if not attrs.get('force_calculation_file') and not attrs.get('experiment_plan_file'):
            raise serializers.ValidationError(
                "Необходимо загрузить хотя бы один файл"
            )
        return attrs


class ImpulsMultipleFileUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки множественных файлов"""
    force_calculation_files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text="Список Excel файлов с расчетом силы"
    )
    experiment_plan_files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text="Список Excel файлов с планом эксперимента"
    )
    
    def validate(self, attrs):
        """Проверяем, что загружен хотя бы один файл"""
        force_files = attrs.get('force_calculation_files', [])
        plan_files = attrs.get('experiment_plan_files', [])
        
        if not force_files and not plan_files:
            raise serializers.ValidationError(
                "Необходимо загрузить хотя бы один файл"
            )
        return attrs


class ImpulsAnalysisBulkDownloadSerializer(serializers.Serializer):
    """Сериализатор для массового скачивания протоколов"""
    analysis_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="Список ID анализов для скачивания протоколов"
    )
    
    def validate_analysis_ids(self, value):
        """Проверяем, что список не пустой"""
        if not value:
            raise serializers.ValidationError("Список ID анализов не может быть пустым")
        return value
