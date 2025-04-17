from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet, PageViewSet, InstanceViewSet

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'instances', InstanceViewSet, basename='instance')

urlpatterns = [
    path('', include(router.urls)),
]