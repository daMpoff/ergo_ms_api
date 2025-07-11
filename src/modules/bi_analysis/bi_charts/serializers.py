from rest_framework import serializers
from src.modules.bi_analysis.bi_charts.models import Chart

class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = [
            'id', 'name', 'description', 'dataset', 'chart_type', 'engine',
            'params', 'options', 'owner', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']