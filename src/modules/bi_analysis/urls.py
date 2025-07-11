from django.urls import path, include

urlpatterns = [
    path('bi_connections/', include('src.modules.bi_analysis.bi_connections.urls')),
    path('bi_datasets/', include('src.modules.bi_analysis.bi_datasets.urls')),
    path('bi_charts/', include('src.modules.bi_analysis.bi_charts.urls')),
]