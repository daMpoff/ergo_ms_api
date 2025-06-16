from rest_framework import serializers
from src.external.bi_analysis.bi_charts.models import Chart

class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = ['id', 'name', 'chart_type', 'config', 'dataset', 'owner', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']
        extra_kwargs = {
            'owner': {'read_only': True}
        }