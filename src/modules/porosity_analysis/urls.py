from django.urls import path, include

from rest_framework.routers import DefaultRouter

from src.modules.porosity_analysis.views import PorosityAnalysisViewSet

router = DefaultRouter()
router.register(r'analyses', PorosityAnalysisViewSet, basename='porosity-analysis')

urlpatterns = [
    path('', include(router.urls)),
]