"""
Базовые классы представлений API.
"""

from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.conf import settings

class BaseAPIView(APIView):
    """
    Базовый класс для всех API представлений.
    
    Включает:
    - JWT аутентификацию
    - Ограничение частоты запросов
    """
    authentication_classes = [JWTAuthentication]
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get_throttle_info(self):
        """Получить информацию о текущих ограничениях запросов."""
        # Отладочная информация
        print("DRF Settings:", getattr(settings, 'REST_FRAMEWORK', {}))
        print("Throttle Rates:", getattr(settings, 'REST_FRAMEWORK', {}).get('DEFAULT_THROTTLE_RATES', {}))
        
        for throttle_class in self.throttle_classes:
            throttle = throttle_class()
            print(f"Throttle class: {throttle_class.__name__}")
            print(f"Scope: {getattr(throttle, 'scope', 'unknown')}")
            print(f"Rate: {throttle.get_rate()}")

        throttle_info = {
            'throttling_enabled': bool(self.throttle_classes),
            'throttle_classes': [
                {
                    'name': throttle_class.__name__,
                    'scope': getattr(throttle_class(), 'scope', 'default'),
                    'rate': self.get_throttle_rate(throttle_class())
                }
                for throttle_class in self.throttle_classes
            ]
        }
        return throttle_info

    def get_throttle_rate(self, throttle):
        """Получить rate limit для конкретного throttle класса."""
        if hasattr(throttle, 'get_rate'):
            return throttle.get_rate()
        return 'unknown'

    def options(self, request, *args, **kwargs):
        """Переопределяем метод OPTIONS для добавления информации о throttling."""
        response = super().options(request, *args, **kwargs)
        response.data['throttle_info'] = self.get_throttle_info()
        return response