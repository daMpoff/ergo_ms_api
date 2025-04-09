from rest_framework import serializers
from .models import StagingGenericData

class StagingGenericDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StagingGenericData
        fields = '__all__'