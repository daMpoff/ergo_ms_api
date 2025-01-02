from django.conf.urls.static import static
from django.urls import (
    path, 
    include
)
from django.conf import settings

from src.config.yasg import urlpatterns as yasg_pattern

urlpatterns = [
    path("api/", include("src.config.urls")),
]

urlpatterns += yasg_pattern

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)