from rest_framework import serializers
from src.modules.bi_analysis.models import ReportConfig

# Создавайте свои сериализаторы здесь
class ReportRunSerializer(serializers.Serializer):
    report_id = serializers.IntegerField(
        help_text="ID отчёта из ReportConfig, который нужно запустить",
        required=True
    )