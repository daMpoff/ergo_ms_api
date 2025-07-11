from django.urls import path

from src.modules.assets_analysis.views import (
    CryptoPriceListAPIView,
    AssetPriceListAPIView,
    StockPriceListAPIView,
    NewsArticleListAPIView,
    ExecuteCommandAPIView,
    PredictCryptoAPIView,
    PredictAssetView,
    PredictStockView,
)

urlpatterns = [
    path('crypto-prices/', CryptoPriceListAPIView.as_view(), name='crypto-price-list'),
    path('assets-prices/', AssetPriceListAPIView.as_view(), name='asset-price-list'),
    path('stock-prices/', StockPriceListAPIView.as_view(), name='stock-price-list'),
    path('news/', NewsArticleListAPIView.as_view(), name='news-article-list'),
    path('execute-command/', ExecuteCommandAPIView.as_view(), name='execute-command'),
    path('predict-crypto/', PredictCryptoAPIView.as_view(), name='predict-crypto'),
    path('predict-asset/', PredictAssetView.as_view(), name='predict-asset'),
    path('predict-stock/', PredictStockView.as_view(), name='predict-stock'),
]