from rest_framework import serializers
from django.contrib.auth.models import User
from src.external.analysis_porosity.models import PorosityAnalysis, PorosityResult, AnalysisFile


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class AnalysisFileSerializer(serializers.ModelSerializer):
    """Сериализатор для файлов результатов анализа"""
    file_url = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    
    class Meta:
        model = AnalysisFile
        fields = [
            'id', 'file_type', 'file_type_display', 'file', 'file_url',
            'filename', 'description', 'created_at'
        ]
        
    def get_file_url(self, obj):
        """Возвращает полный URL файла"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class PorosityResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов анализа пористости"""
    
    class Meta:
        model = PorosityResult
        fields = [
            'porosity_percentage', 'relative_pore_area', 'number_of_pores',
            'mean_pore_size_microns', 'median_pore_size_microns',
            'mean_pore_diameter_microns', 'median_pore_diameter_microns',
            'pixels_per_micron', 'scale_region_x', 'scale_region_y',
            'scale_region_width', 'scale_region_height', 'total_pixels',
            'scale_excluded_pixels', 'lines_excluded_pixels',
            'anomalies_excluded_pixels', 'total_excluded_pixels',
            'extended_metrics', 'created_at'
        ]


class PorosityAnalysisListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка анализов пористости"""
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    original_image_url = serializers.SerializerMethodField()
    has_result = serializers.SerializerMethodField()
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'user', 'title', 'description', 'original_image',
            'original_image_url', 'scale_value', 'status', 'status_display',
            'has_result', 'created_at', 'updated_at', 'processed_at'
        ]
        
    def get_original_image_url(self, obj):
        """Возвращает полный URL исходного изображения"""
        if obj.original_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.original_image.url)
            return obj.original_image.url
        return None
        
    def get_has_result(self, obj):
        """Проверяет, есть ли результаты анализа"""
        return hasattr(obj, 'result')


class PorosityAnalysisDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации об анализе"""
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    original_image_url = serializers.SerializerMethodField()
    result = PorosityResultSerializer(read_only=True)
    files = AnalysisFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = PorosityAnalysis
        fields = [
            'id', 'user', 'title', 'description', 'original_image',
            'original_image_url', 'scale_value', 'status', 'status_display',
            'error_message', 'result', 'files', 'created_at', 'updated_at', 'processed_at'
        ]
        
    def get_original_image_url(self, obj):
        """Возвращает полный URL исходного изображения"""
        if obj.original_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.original_image.url)
            return obj.original_image.url
        return None


class PorosityAnalysisCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания нового анализа пористости"""
    
    class Meta:
        model = PorosityAnalysis
        fields = ['title', 'description', 'original_image', 'scale_value']
        
    def validate_original_image(self, value):
        """Валидация загружаемого изображения"""
        if value:
            # Проверка размера файла (максимум 10 МБ)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Размер файла не должен превышать 10 МБ")
                
            # Проверка типа файла
            allowed_types = ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Поддерживаются только файлы форматов: JPEG, PNG, BMP, TIFF"
                )
                
        return value
        
    def validate_scale_value(self, value):
        """Валидация значения шкалы"""
        if value <= 0:
            raise serializers.ValidationError("Значение шкалы должно быть положительным числом")
        if value > 10000:
            raise serializers.ValidationError("Значение шкалы не должно превышать 10000 мкм")
        return value
        
    def create(self, validated_data):
        """Создание нового анализа с привязкой к текущему пользователю"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PorosityAnalysisUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления анализа пористости"""
    
    class Meta:
        model = PorosityAnalysis
        fields = ['title', 'description']
        
    def validate(self, attrs):
        """Валидация обновления"""
        # Проверяем, что анализ еще не обработан
        if self.instance.status in ['processing', 'completed']:
            raise serializers.ValidationError(
                "Нельзя изменять обработанный или обрабатываемый анализ"
            )
        return attrs


class BatchAnalysisCreateSerializer(serializers.Serializer):
    """Сериализатор для пакетного создания анализов"""
    
    images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False),
        min_length=1,
        max_length=20,  # Максимум 20 файлов за раз
        help_text="Список изображений для анализа (максимум 20)"
    )
    
    scale_value = serializers.FloatField(
        min_value=0.1,
        max_value=10000,
        help_text="Общее значение шкалы для всех анализов"
    )
    
    base_title = serializers.CharField(
        max_length=150,
        help_text="Базовое название для анализов (к каждому добавится номер)"
    )
    
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Общее описание для всех анализов"
    )
    
    def validate_images(self, value):
        """Валидация списка изображений"""
        errors = []
        
        for i, image in enumerate(value):
            # Проверка размера файла (максимум 10 МБ)
            if image.size > 10 * 1024 * 1024:
                errors.append(f"Файл {i+1}: размер не должен превышать 10 МБ")
                
            # Проверка типа файла
            allowed_types = ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff']
            if image.content_type not in allowed_types:
                errors.append(f"Файл {i+1}: поддерживаются только JPEG, PNG, BMP, TIFF")
        
        if errors:
            raise serializers.ValidationError(errors)
            
        return value
    
    def validate_scale_value(self, value):
        """Валидация значения шкалы"""
        if value <= 0:
            raise serializers.ValidationError("Значение шкалы должно быть положительным числом")
        if value > 10000:
            raise serializers.ValidationError("Значение шкалы не должно превышать 10000 мкм")
        return value
    
    def create(self, validated_data):
        """Создание пакета анализов"""
        user = self.context['request'].user
        images = validated_data['images']
        scale_value = validated_data['scale_value']
        base_title = validated_data['base_title']
        description = validated_data.get('description', '')
        
        created_analyses = []
        
        for i, image in enumerate(images, 1):
            # Создаем уникальное название для каждого анализа
            title = f"{base_title} #{i:02d}"
            if len(images) == 1:
                title = base_title  # Если только один файл, не добавляем номер
            
            analysis = PorosityAnalysis.objects.create(
                user=user,
                title=title,
                description=description,
                original_image=image,
                scale_value=scale_value
            )
            
            created_analyses.append(analysis)
        
        return created_analyses


class BatchAnalysisStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса пакетного анализа"""
    
    total_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    processing_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    analyses = PorosityAnalysisListSerializer(many=True, read_only=True)