from django.urls import path, include
from django.http import JsonResponse

def bi_root(request):
    return JsonResponse({
        "message": "Добро пожаловать в BI-модуль",
        "endpoints": [
            "/api/bi_analysis/storage_data/",
            "/api/bi_analysis/datawarehouse/",
        ]
    })

urlpatterns = [
    path('', bi_root, name='bi-root'),
    path('storage_data/', include('src.external.bi_analysis.storage_data.urls')),
    path('datawarehouse/', include('src.external.bi_analysis.datawarehouse.urls')),
]