from django.urls import path, include

urlpatterns = [
    path('bi_datasets/', include('src.modules.bi_analysis.bi_datasets.urls')),
]