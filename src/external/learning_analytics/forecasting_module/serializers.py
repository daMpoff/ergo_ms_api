# Импорт необходимых классов и модулей из Django REST Framework
from rest_framework.serializers import (
    ModelSerializer,  # Базовый класс для создания сериализаторов на основе моделей
    CharField,       # Поле для строковых данных
    BooleanField,    # Поле для булевых значений
    ValidationError, # Класс для обработки ошибок валидации
    Serializer       # Базовый класс для создания кастомных сериализаторов
)

# Импорт модели Technology из приложения learning_analytics
from src.external.learning_analytics.forecasting_module.models import (
    Speciality
)

# Создание сериализатора для модели Speciality
class SpecialitySerializer(ModelSerializer):
    class Meta:
        # Указываем модель, с которой работает сериализатор
        model = Speciality
        # Указываем поля модели, которые будут сериализованы/десериализованы
        fields = ['code', 'name', 'specialization', 'department', 'faculty', 'education_duration', 'year_of_admission']

        # Метод для создания нового объекта Speciality
        def create(self, validated_data):
            """
            Создаёт новый объект Speciality на основе валидированных данных

            :param validated_data: Данные, прошедшие валидацию
            :return: Созданный объект Speciality
            """
            speciality = Speciality.objects.create(
                code=validated_data['code'],                             # Устанавливаем код специальности
                name=validated_data['name'],                             # Устанавливаем наименование специальности
                specialization=validated_data['specialization'],         # Устанавливаем специализацию специальности
                department=validated_data['department'],                 # Устанавливаем кафедру специальности
                faculty=validated_data['faculty'],                       # Устанавливаем факультет специальности
                education_duration=validated_data['education_duration'], # Устанавливаем продолжительность обучения по специальности
                year_of_admission=validated_data['year_of_admission'],   # Устанавливаем год поступления на специальность
            )

            return speciality # Возвращаем созданный объект