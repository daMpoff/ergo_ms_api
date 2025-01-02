from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.contrib.auth import authenticate
from django.utils.crypto import get_random_string

from src.core.standard_functions.methods import (
    parse_errors_to_dict, 
    send_confirmation_email
)
from src.core.modules.cms.adp.models import EmailConfirmationCode
from src.core.modules.cms.adp.serializers import (
    UserLoginSerializer, 
    UserRegistrationSerializer,
    UserRegistrationValidationSerializer,
)

class UserRegistrationValidationView(APIView):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    @swagger_auto_schema(
        operation_description="Регистрация нового пользователя.",

        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,

            properties={
                'first_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя'
                ),
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Логин'
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format=openapi.FORMAT_EMAIL, 
                    description='Электронная почта'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format=openapi.FORMAT_PASSWORD, 
                    description='Пароль'
                ),
                'password_confirm': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format=openapi.FORMAT_PASSWORD, 
                    description='Подтверждение пароля'
                ),
                'is_superuser': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,                      
                    description='Является ли суперпользователем'
                ),
            },

            required=['first_name', 'username', 'email', 'password', 'password_confirm'],

            example={
                'first_name': 'Евгений',
                'username': 'Dohao',
                'email': 'muzalevskij.evgenij@mail.ru',
                'password': 'securepassword123',
                'password_confirm': 'securepassword123',
                'is_superuser': False,
            }
        ),
        responses={
            201: "Пользователь успешно зарегистрирован.",
            400: "Регистрация не успешна."
        },
    )
    def post(self, request):
        serializer = UserRegistrationValidationSerializer(data=request.data)

        if serializer.is_valid():
            successful_response = Response(
                {"message": "Валидация успешна."}, 
                status=status.HTTP_200_OK
            )
            return successful_response

        errors = parse_errors_to_dict(serializer.errors)
        return Response(
            errors, 
            status=status.HTTP_400_BAD_REQUEST
        )

class SendConfirmationCodeView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Отсутствует Email"}, status=status.HTTP_400_BAD_REQUEST)

        # Генерация 6-значного кода
        code = get_random_string(length=6, allowed_chars='0123456789')
        
        # Обновляем или создаём запись для email
        _ = EmailConfirmationCode.objects.update_or_create(
            email=email,
            defaults={"code": code},
        )
        
        # Отправляем email
        send_confirmation_email(email, code)

        return Response({"message": "Confirmation code sent"}, status=status.HTTP_200_OK)

class VerifyConfirmationCodeView(APIView):
    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response({"error": "Email and code are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            confirmation_code = EmailConfirmationCode.objects.get(email=email)
        except EmailConfirmationCode.DoesNotExist:
            return Response({"error": "Invalid email or code"}, status=status.HTTP_400_BAD_REQUEST)

        if confirmation_code.code == code:
            # Код верен, можно выполнить дальнейшие действия
            # Удаляем запись после успешной проверки
            confirmation_code.delete()
            return Response({"message": "Code verified successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)
        
class UserRegistrationView(APIView):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    @swagger_auto_schema(
        operation_description="Проверка регистрации.",

        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,

            properties={
                'first_name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя'
                ),
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Логин'
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format=openapi.FORMAT_EMAIL, 
                    description='Электронная почта'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format=openapi.FORMAT_PASSWORD, 
                    description='Пароль'
                ),
                'password_confirm': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format=openapi.FORMAT_PASSWORD, 
                    description='Подтверждение пароля'
                ),
                'is_superuser': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,                      
                    description='Является ли суперпользователем'
                ),
            },

            required=['first_name', 'username', 'email', 'password', 'password_confirm'],

            example={
                'first_name': 'Евгений',
                'username': 'Dohao',
                'email': 'muzalevskij.evgenij@mail.ru',
                'password': 'securepassword123',
                'password_confirm': 'securepassword123',
                'is_superuser': False,
            }
        ),
        responses={
            201: "Пользователь успешно зарегистрирован.",
            400: "Регистрация не успешна."
        },
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            successful_response = Response(
                {"message": "Регистрация успешна."}, 
                status=status.HTTP_200_OK
            )
            return successful_response

        errors = parse_errors_to_dict(serializer.errors)
        return Response(
            errors, 
            status=status.HTTP_400_BAD_REQUEST
        )

class UserAuthorizationView(APIView):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    @swagger_auto_schema(
        operation_description="Авторизация пользователя.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Логин'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description='Пароль'
                ),
                'password_confirm': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description='Подтверждение пароля'
                ),
            },
            required=['username', 'password', 'password_confirm'],
            example={
                'username': 'Dohao',
                'password': 'securepassword123',
                'password_confirm': 'securepassword123',
            }
        ),
        responses={
            200: openapi.Response(
                description="Пользователь успешно авторизован.",
                examples={
                    "application/json": {
                        "refresh": "your_refresh_token",
                        "access": "your_access_token"
                    }
                }
            ),
            400: "Авторизация не успешна."
        },
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "message": "Неверные учетные данные."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        errors = parse_errors_to_dict(serializer.errors)
        return Response(
            errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    @swagger_auto_schema(
        operation_description="Защищенное представление.",
        security=[{"Bearer": []}],
        responses={
            200: "Вы авторизованы.",
            401: "Неавторизованный доступ."
        },
    )
    def get(self, request):
        return Response(
            {"message": "Вы авторизованы."}, 
            status=status.HTTP_200_OK
        )