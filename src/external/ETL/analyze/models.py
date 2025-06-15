from django.db import models
from django.utils import timezone

# Модель для цен криптовалют
class CryptoPrice(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    price_usd = models.DecimalField(max_digits=20, decimal_places=8)
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ('name', 'timestamp')
        indexes = [
            models.Index(fields=['name', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')} - ${self.price_usd}"


# Модель для цен активов
class AssetPrice(models.Model):
    name_usd = models.CharField(max_length=50)
    price_usd = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    name_rub = models.CharField(max_length=50, null=True, blank=True)
    price_rub = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('name_usd', 'timestamp')


# Модель для новостей
class NewsArticle(models.Model):
    SENTIMENT_LABELS = [
        ('positive', 'Позитивная'),
        ('negative', 'Негативная'),
        ('neutral', 'Нейтральная'),
        ('skipped', 'Пропущено'),
    ]

    title = models.CharField(max_length=512)
    url = models.URLField(max_length=1024, unique=True, db_index=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    published_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(default=timezone.now)
    relevant_coins = models.JSONField(default=list, blank=True, db_index=True)

    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Числовая оценка тональности"
    )
    sentiment_label = models.CharField(
        max_length=10,
        choices=SENTIMENT_LABELS,
        null=True,
        blank=True,
        db_index=True,
        help_text="Категориальная оценка тональности (positive/negative/neutral)"
    )
    manual_label = models.CharField(
        max_length=10,
        choices=SENTIMENT_LABELS[:-1],
        null=True,
        blank=True,
        help_text="Ручная разметка тональности (хорошая/плохая/нейтральная новость)"
    )

    class Meta:
        indexes = [
            models.Index(fields=['published_at']),
            models.Index(fields=['sentiment_label']),
            models.Index(fields=['manual_label']),
        ]
        ordering = ['-published_at']

    def __str__(self):
        label_display = self.get_sentiment_label_display() if self.sentiment_label else 'N/A'
        return f"[{self.published_at.strftime('%Y-%m-%d')}] {self.title[:80]}... ({label_display})"

class StockPrice(models.Model):
    """
    Модель для хранения цен на акции (например, Лукойл, Tesla и др.).
    """
    ticker = models.CharField(max_length=20, db_index=True, help_text="Биржевой тикер акции")
    timestamp = models.DateTimeField(db_index=True, help_text="Дата и время цены")
    price_usd = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True,
                                    help_text="Цена в долларах США")
    price_rub = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True,
                                    help_text="Цена в российских рублях")
    close_price = models.DecimalField(max_digits=20, decimal_places=8, help_text="Цена закрытия (основное поле цены)")
    volume = models.BigIntegerField(null=True, blank=True, help_text="Объем торгов")

    class Meta:
        unique_together = ('ticker', 'timestamp')

        indexes = [
            models.Index(fields=['ticker', 'timestamp']),
        ]
        ordering = ['-timestamp']
        verbose_name = "Цена акции"
        verbose_name_plural = "Цены акций"

    def __str__(self):
        price = self.price_usd if self.price_usd is not None else self.price_rub
        currency = "$" if self.price_usd is not None else "₽"
        return f"{self.ticker} - {self.timestamp.strftime('%Y-%m-%d %H:%M')} - {currency}{price}"