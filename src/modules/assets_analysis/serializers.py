from rest_framework import serializers

from src.modules.assets_analysis.models import CryptoPrice, NewsArticle, AssetPrice, StockPrice

class CryptoPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoPrice
        fields = ['id', 'name', 'price_usd', 'timestamp']
        ref_name = 'CryptoPriceSerializer_External'

class AssetPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPrice
        fields = ['id', 'name_usd', 'price_usd', 'name_rub', 'price_rub', 'timestamp']
        ref_name = 'AssetPriceSerializer_External'

class StockPriceSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели цен на акции.
    """
    class Meta:
        model = StockPrice
        fields = [
            'id',
            'ticker',
            'timestamp',
            'price_usd',
            'price_rub'
        ]
        ref_name = 'StockPriceSerializer_External'

class NewsArticleSerializer(serializers.ModelSerializer):
    sentiment_display = serializers.CharField(source='get_sentiment_label_display', read_only=True)
    manual_label_display = serializers.CharField(source='get_manual_label_display', read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            'id',
            'title',
            'url',
            'source',
            'summary',
            'published_at',
            'fetched_at',
            'relevant_coins',
            'sentiment_score',
            'sentiment_label',
            'sentiment_display',
            'manual_label',
            'manual_label_display'
        ]
        read_only_fields = ['fetched_at', 'sentiment_score', 'sentiment_label', 'sentiment_display', 'manual_label_display']
        ref_name = 'NewsArticleSerializer_External'