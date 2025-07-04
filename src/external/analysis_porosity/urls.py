from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.external.analysis_porosity.views import PorosityAnalysisViewSet

# Создаем роутер для ViewSet
router = DefaultRouter()
router.register(r'analyses', PorosityAnalysisViewSet, basename='porosity-analysis')

app_name = 'analysis_porosity'

urlpatterns = [
    # API маршруты через роутер
    path('api/', include(router.urls)),
    
    # Дополнительные маршруты можно добавить здесь при необходимости
]

# Доступные API эндпоинты:
# GET /api/analyses/ - список анализов пользователя
# POST /api/analyses/ - создание нового анализа (автоматически запускает обработку)
# GET /api/analyses/{id}/ - детальная информация об анализе
# PUT /api/analyses/{id}/ - обновление анализа (только название и описание)
# PATCH /api/analyses/{id}/ - частичное обновление анализа
# DELETE /api/analyses/{id}/ - удаление анализа (если не обрабатывается)
# POST /api/analyses/{id}/start_analysis/ - ручной запуск анализа
# GET /api/analyses/{id}/status/ - получение статуса анализа
# GET /api/analyses/{id}/result/ - получение результатов анализа
# GET /api/analyses/{id}/files/ - получение файлов результатов