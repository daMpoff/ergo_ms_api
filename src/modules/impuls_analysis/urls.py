from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImpulsAnalysisViewSet, ImpulsFileViewSet, ImpulsProtocolViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'analyses', ImpulsAnalysisViewSet, basename='impuls-analysis')
router.register(r'files', ImpulsFileViewSet, basename='impuls-file')
router.register(r'protocols', ImpulsProtocolViewSet, basename='impuls-protocol')

urlpatterns = [
    # Подключаем роутер
    path('', include(router.urls)),
]