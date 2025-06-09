from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.external.porosity_analysis.views import PorosityAnalysisViewSet

router = DefaultRouter()
router.register(r'analysis', PorosityAnalysisViewSet, basename='porosity-analysis')

urlpatterns = [
    path('', include(router.urls)),
]