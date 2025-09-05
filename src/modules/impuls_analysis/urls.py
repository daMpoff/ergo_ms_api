from django.urls import path, include
from rest_framework.routers import DefaultRouter

from src.modules.impuls_analysis.views import ImpulsAnalysisViewSet

router = DefaultRouter()
router.register(r'analyses', ImpulsAnalysisViewSet, basename='impuls-analysis')

urlpatterns = [
    path('', include(router.urls)),
]