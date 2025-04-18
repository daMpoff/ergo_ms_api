from rest_framework import serializers
from .models import Connection

class ConnectionSerializer(serializers.ModelSerializer):
    connector_type_display = serializers.CharField(source='get_connector_type_display', read_only=True)

    class Meta:
        model = Connection
        fields = [
            'id', 'name', 'connector_type', 'connector_type_display',
            'config', 'created_at', 'owner'
        ]
        read_only_fields = ['id', 'created_at', 'owner']