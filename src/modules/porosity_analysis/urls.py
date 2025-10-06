from django.urls import path, include

from rest_framework.routers import DefaultRouter

from src.modules.porosity_analysis.views import (
    PorosityAnalysisViewSet, 
    PorosityGroupViewSet, 
    PorosityArchiveViewSet,
    DownloadByTokenView
)

router = DefaultRouter()
router.register(r'analyses', PorosityAnalysisViewSet, basename='porosity-analysis')
router.register(r'groups', PorosityGroupViewSet, basename='porosity-analysis-group')
router.register(r'archives', PorosityArchiveViewSet, basename='porosity-analysis-archive')

urlpatterns = [
    path('', include(router.urls)),
    # Прямой маршрут для скачивания по токену
    path('download/<uuid:token>/', DownloadByTokenView.as_view({'get': 'download_by_token'}), name='download-by-token'),
]