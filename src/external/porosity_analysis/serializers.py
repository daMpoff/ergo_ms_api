from rest_framework import serializers
from drf_yasg import openapi
from drf_yasg.utils import swagger_serializer_method
from src.external.porosity_analysis.models import PorosityAnalysis, PorosityImage, PorosityResults, PorosityVisualization


class PorosityImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений анализа"""
    
    class Meta:
        model = PorosityImage
        fields = [
            'id', 'original_image', 'filename', 
            'image_porosity_percentage', 'image_number_of_pores', 
            'image_average_pore_diameter', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PorosityVisualizationSerializer(serializers.ModelSerializer):
    """Сериализатор для визуализаций"""
    
    class Meta:
        model = PorosityVisualization
        fields = ['id', 'visualization_type', 'file_path', 'created_at']
        read_only_fields = ['id', 'created_at']


class PorosityResultsSerializer(serializers.ModelSerializer):
    """Сериализатор для детальных результатов"""
    
    class Meta:
        model = PorosityResults
        fields = [
            'pore_size_distribution', 'interpore_distances', 
            'pore_orientation', 'pore_shapes', 'scale_info', 
            'excluded_areas', 'created_at'
        ]
        read_only_fields = ['created_at']


class PorosityAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для анализа пористости"""
    
    images = PorosityImageSerializer(many=True, read_only=True)
    visualizations = PorosityVisualizationSerializer(many=True, read_only=True)
    detailed_results = PorosityResultsSerializer(read_only=True)
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'name', 'status', 'scale_value', 
            'porosity_percentage', 'number_of_pores', 
            'average_pore_diameter', 'total_pore_area',
            'created_at', 'updated_at', 'error_message',
            'images', 'visualizations', 'detailed_results'
        ]
        read_only_fields = [
            'id', 'status', 'porosity_percentage', 'number_of_pores',
            'average_pore_diameter', 'total_pore_area', 'created_at', 
            'updated_at', 'error_message'
        ]


class PorosityAnalysisListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка анализов"""
    
    images_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'name', 'status', 'scale_value',
            'porosity_percentage', 'number_of_pores',
            'created_at', 'updated_at', 'images_count'
        ]
    
    def get_images_count(self, obj):
        """Возвращает количество изображений в анализе"""
        return obj.images.count()


class PorosityAnalysisCreateSerializer(serializers.Serializer):
    """Сериализатор для создания анализа"""
    
    name = serializers.CharField(max_length=255)
    scale_value = serializers.FloatField(default=100.0, min_value=0.1, max_value=10000.0)
    
    # Используем отдельные поля вместо ListField для избежания проблем со Swagger
    # Все поля делаем необязательными, но валидируем что хотя бы одно есть
    image_1 = serializers.ImageField(required=False, help_text="Первое изображение для анализа")
    image_2 = serializers.ImageField(required=False, help_text="Второе изображение для анализа")
    image_3 = serializers.ImageField(required=False, help_text="Третье изображение для анализа")
    image_4 = serializers.ImageField(required=False, help_text="Четвертое изображение для анализа")
    image_5 = serializers.ImageField(required=False, help_text="Пятое изображение для анализа")
    image_6 = serializers.ImageField(required=False, help_text="Шестое изображение для анализа")
    image_7 = serializers.ImageField(required=False, help_text="Седьмое изображение для анализа")
    image_8 = serializers.ImageField(required=False, help_text="Восьмое изображение для анализа")
    image_9 = serializers.ImageField(required=False, help_text="Девятое изображение для анализа")
    image_10 = serializers.ImageField(required=False, help_text="Десятое изображение для анализа")
    
    def validate(self, data):
        """Собираем все переданные изображения в список"""
        images = []
        
        # Проверяем отдельные поля изображений
        for i in range(1, 11):
            image_field = f'image_{i}'
            if image_field in data and data[image_field]:
                images.append(data[image_field])
        
        if not images:
            raise serializers.ValidationError("Необходимо загрузить хотя бы одно изображение")
        
        if len(images) > 10:
            raise serializers.ValidationError("Максимально можно загрузить 10 изображений")
        
        # Валидация изображений
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        max_size = 50 * 1024 * 1024  # 50MB
        
        for image in images:
            # Проверка расширения
            if not any(image.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    f"Неподдерживаемый формат файла: {image.name}. "
                    f"Поддерживаются: {', '.join(allowed_extensions)}"
                )
            
            # Проверка размера
            if image.size > max_size:
                raise serializers.ValidationError(
                    f"Файл {image.name} слишком большой. "
                    f"Максимальный размер: 50MB"
                )
        
        # Добавляем собранные изображения в validated_data
        data['images'] = images
        return data