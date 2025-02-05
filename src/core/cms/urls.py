from django.urls import (
    path, include
)

urlpatterns = [
    path('adp/', include('src.core.cms.adp.urls')),
]