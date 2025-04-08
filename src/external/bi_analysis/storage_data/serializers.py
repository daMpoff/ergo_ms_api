from rest_framework import serializers
from .models import GenericStorage

class GenericStorageSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False)
    json_data = serializers.JSONField(required=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = GenericStorage
        fields = '__all__'