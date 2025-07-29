from django.urls import path, include
from rest_framework.routers import DefaultRouter

from src.modules.video_analysis.views import VideoAnalysisViewSet

router = DefaultRouter()
router.register(r'video-analysis', VideoAnalysisViewSet, basename='video-analysis')

urlpatterns = [
    path('', include(router.urls)),
] 