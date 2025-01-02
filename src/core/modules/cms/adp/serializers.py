from rest_framework.serializers import (
    ModelSerializer,
    CharField,
    BooleanField,
    ValidationError,
    Serializer
)

from django.contrib.auth.models import User

class UserRegistrationValidationSerializer(Serializer):
    first_name = CharField(required=True)
    username = CharField(required=True)
    email = CharField(required=True)
    password = CharField(write_only=True, style={'input_type': 'password'})
    is_superuser = BooleanField(required=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise ValidationError("Данный логин уже занят, попробуйте другой.")
        return value

    def validate(self, attrs):
        return attrs

class UserRegistrationSerializer(ModelSerializer):
    password = CharField(
        write_only=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password', 'is_superuser']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_superuser=validated_data['is_superuser'],
        )

        return user
    
class UserLoginSerializer(Serializer):
    username = CharField(max_length=150)
    password = CharField(write_only=True)