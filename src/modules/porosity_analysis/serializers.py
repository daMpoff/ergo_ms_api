from rest_framework import serializers
from src.modules.porosity_analysis.models import PorosityAnalysis


class PorosityAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для анализа пористости"""
    
    result_files = serializers.SerializerMethodField()
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'name', 'description', 'created_at', 'original_image_uuid',
            'results_uuid', 'scale_value', 'pixels_per_micron', 'porosity_percentage',
            'number_of_pores', 'average_pore_size', 'max_pore_size', 'min_pore_size',
            'pore_density', 'average_interpore_distance', 'status', 'error_message', 'result_files'
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


class CreatePorosityAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для создания нового анализа пористости"""
    
    class Meta:
        model = PorosityAnalysis
        fields = ['id', 'name', 'description', 'scale_value', 'pixels_per_micron']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        import uuid
        
        # Генерируем UUID для файлов
        validated_data['original_image_uuid'] = str(uuid.uuid4())
        validated_data['results_uuid'] = str(uuid.uuid4())
        
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