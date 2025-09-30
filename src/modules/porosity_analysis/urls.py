from django.urls import path, include

from rest_framework.routers import DefaultRouter

from src.modules.porosity_analysis.views import PorosityAnalysisViewSet, PorosityGroupViewSet

router = DefaultRouter()
router.register(r'analyses', PorosityAnalysisViewSet, basename='porosity-analysis')
router.register(r'groups', PorosityGroupViewSet, basename='porosity-analysis-group')

urlpatterns = [
    path('', include(router.urls)),
]