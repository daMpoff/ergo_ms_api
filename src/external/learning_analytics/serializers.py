# Импорт необходимых классов и модулей из Django REST Framework
from rest_framework.serializers import (
    ModelSerializer,  # Базовый класс для создания сериализаторов на основе моделей
    CharField,       # Поле для строковых данных
    BooleanField,    # Поле для булевых значений
    ValidationError, # Класс для обработки ошибок валидации
    Serializer       # Базовый класс для создания кастомных сериализаторов
)

# Импорт необходимых моделей
from src.external.learning_analytics.models import (
    Employer        # Модель работодателя
)


# Создание сериализатора для модели Employer
class EmployerSerializer(ModelSerializer):
    class Meta:
        model = Employer
        fields = ['id', 'company_name', 'description', 'email', 'rating', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']  # Указываем, что эти поля только для чтения

    def create(self, validated_data):
        """
        Создает новый объект Employer на основе валидированных данных.
        """
        employer = Employer.objects.create(
            company_name=validated_data['company_name'],
            description=validated_data['description'],
            email=validated_data['email'],
            rating=validated_data['rating']
        )
        return employer

    def validate_rating(self, value):
        """
        Проверяет, что рейтинг находится в диапазоне от 1 до 5.
        """
        if value < 0 or value > 5:
            raise Serializer.ValidationError("Рейтинг должен быть от 1 до 5.")
        return value