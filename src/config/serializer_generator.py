from rest_framework import serializers

def create_serializer_class(name, data_example):
    """
    Динамически создает класс сериализатора на основе примера данных.
    """
    fields = {}
    
    def _get_field_type(value):
        if isinstance(value, dict):
            # Рекурсивно создаем вложенный сериализатор
            nested_serializer = create_serializer_class(
                f"{name}Nested{len(fields)}", 
                value
            )
            return nested_serializer
        elif isinstance(value, list):
            if value:  # Если список не пустой
                # Создаем сериализатор для элементов списка
                item_serializer = _get_field_type(value[0])
                return serializers.ListSerializer(child=item_serializer)
            return serializers.ListField()
        elif isinstance(value, int):
            return serializers.IntegerField()
        elif isinstance(value, float):
            return serializers.FloatField()
        elif isinstance(value, bool):
            return serializers.BooleanField()
        elif value is None:
            return serializers.CharField(allow_null=True)
        else:
            return serializers.CharField()

    # Создаем поля сериализатора на основе структуры данных
    for key, value in data_example.items():
        if isinstance(value, dict):
            fields[key] = _get_field_type(value)()
        else:
            fields[key] = _get_field_type(value)()

    # Создаем класс сериализатора
    return type(
        f'Dynamic{name}Serializer',
        (serializers.Serializer,),
        fields
    ) 