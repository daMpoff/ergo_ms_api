from rest_framework import serializers
from .models import Dataset, FileUpload

class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            'id',
            'name',
            'description',
            'owner',
            'file_source',
            'connection',
            'table_ref',
            'created_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at']
        extra_kwargs = {
            'owner': {'read_only': True}
        }
        
class FileUploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FileUpload
        fields = [
            'id', 'name', 'file', 'file_url', 'uploaded_at',
            'owner', 'original_filename', 'file_type', 'connection'
        ]
        read_only_fields = ['id', 'uploaded_at']
        extra_kwargs = {
            'owner': {'read_only': True},
        }

    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None