from rest_framework import serializers
from .models import GenericStorage
from django.contrib.auth import get_user_model

class GenericStorageSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False)
    json_data = serializers.JSONField(required=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    owner_username = serializers.SerializerMethodField()
    storage_type = serializers.CharField()

    class Meta:
        model = GenericStorage
        fields = '__all__'
    
    def get_owner_username(self, obj):
        return obj.owner.username if obj.owner else None