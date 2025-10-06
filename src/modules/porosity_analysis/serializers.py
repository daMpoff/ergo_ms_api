from rest_framework import serializers
from src.modules.porosity_analysis.models import PorosityAnalysis, PorosityGroup, PorosityArchive
from django.utils import timezone


class PorosityGroupSerializer(serializers.ModelSerializer):
    """Сериализатор группы анализов пористости"""

    class Meta:
        model = PorosityGroup
        fields = ['id', 'name', 'description', 'created_at']


class PorosityArchiveSerializer(serializers.ModelSerializer):
    """Сериализатор архива отчетов пористости"""
    
    file_size_mb = serializers.ReadOnlyField()
    analyses_count = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_failed = serializers.ReadOnlyField()
    is_creating = serializers.ReadOnlyField()
    
    class Meta:
        model = PorosityArchive
        fields = [
            'id', 'uuid', 'name', 'description', 'created_at', 'file_path', 
            'file_size', 'file_size_mb', 'report_type', 'status', 
            'error_message', 'analyses_count', 'is_completed', 
            'is_failed', 'is_creating'
        ]
        read_only_fields = ['created_at', 'file_size', 'file_size_mb', 'analyses_count']


class CreatePorosityArchiveSerializer(serializers.ModelSerializer):
    """Сериализатор для создания архива отчетов"""
    
    analysis_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="Список ID анализов для включения в архив"
    )
    input_text = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Строка с номерами анализов через запятую или тире"
    )
    
    class Meta:
        model = PorosityArchive
        fields = [
            'name', 'description', 'report_type', 'analysis_ids', 'input_text'
        ]
    
    def validate_report_type(self, value):
        if value not in ['pdf', 'docx']:
            raise serializers.ValidationError("Тип отчета должен быть 'pdf' или 'docx'")
        return value
    
    def validate(self, attrs):
        analysis_ids = attrs.get('analysis_ids', [])
        input_text = attrs.get('input_text', '')
        
        if not analysis_ids and not input_text.strip():
            raise serializers.ValidationError(
                "Необходимо указать либо analysis_ids, либо input_text"
            )
        
        return attrs


class PorosityAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для анализа пористости"""
    
    result_files = serializers.SerializerMethodField()
    duration_human = serializers.SerializerMethodField()
    group = PorosityGroupSerializer(read_only=True)
    group_id = serializers.IntegerField(source='group.id', read_only=True)
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'name', 'description', 'created_at', 'start_time', 'end_time', 'original_image_uuid',
            'results_uuid', 'scale_value', 'pixels_per_micron', 'porosity_percentage',
            'number_of_pores', 'average_pore_size', 'max_pore_size', 'min_pore_size',
            'pore_density', 'average_interpore_distance', 'status', 'error_message', 'result_files',
            'duration_seconds', 'duration_human', 'group', 'group_id'
        ]
        read_only_fields = [
            'id', 'created_at', 'original_image_uuid', 'results_uuid',
            'porosity_percentage', 'number_of_pores', 'average_pore_size',
            'max_pore_size', 'min_pore_size', 'pore_density',
            'average_interpore_distance', 'status', 'error_message'
        ]
    
    def get_result_files(self, obj):
        """Возвращает список файлов результатов"""
        return obj.get_result_files()

    def get_duration_human(self, obj):
        seconds = obj.duration_seconds
        if seconds is None:
            return None
        # формат: HH:MM:SS (точность до секунд)
        try:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            if h > 0:
                return f"{h:02d}:{m:02d}:{s:02d}"
            else:
                return f"{m:02d}:{s:02d}"
        except Exception:
            return None


class CreatePorosityAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для создания нового анализа пористости"""
    
    # Доп. поля для назначения/создания группы
    group_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    new_group_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = PorosityAnalysis
        fields = ['id', 'name', 'description', 'scale_value', 'pixels_per_micron', 'group_id', 'new_group_name']
        read_only_fields = ['id']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True}
        }
    
    def create(self, validated_data):
        import uuid
        group_id = validated_data.pop('group_id', None)
        new_group_name = validated_data.pop('new_group_name', '').strip()
        
        # Генерируем UUID для файлов
        validated_data['original_image_uuid'] = str(uuid.uuid4())
        validated_data['results_uuid'] = str(uuid.uuid4())
        
        # Автогенерация названия, если не указано пользователем (без даты/времени)
        name = validated_data.get('name')
        if not name or not str(name).strip():
            validated_data['name'] = "Анализ пористости"
        
        # Привязка к группе, если указана
        group_instance = None
        try:
            if new_group_name:
                group_instance, _ = PorosityGroup.objects.get_or_create(name=new_group_name)
            elif group_id:
                group_instance = PorosityGroup.objects.filter(id=group_id).first()
        except Exception:
            group_instance = None

        if group_instance is not None:
            validated_data['group'] = group_instance

        # Создаем объект анализа
        analysis = PorosityAnalysis.objects.create(**validated_data)
        
        return analysis


class PorosityAnalysisStatusSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения статуса анализа"""
    
    class Meta:
        model = PorosityAnalysis
        fields = ['id', 'name', 'status', 'created_at', 'error_message']


class PorosityAnalysisResultsSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения результатов анализа"""
    
    result_files = serializers.SerializerMethodField()
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'name', 'porosity_percentage', 'number_of_pores',
            'average_pore_size', 'max_pore_size', 'min_pore_size',
            'pore_density', 'average_interpore_distance', 'status', 'result_files'
        ]
    
    def get_result_files(self, obj):
        """Возвращает список файлов результатов"""
        return obj.get_result_files()