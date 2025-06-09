from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_yasg import openapi
from ..bi_connections.models import Connection
from .models import FileUpload, Dataset, DataSetTable, DataSetField

User = get_user_model()

class DataSetTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSetTable
        fields = ['id', 'dataset', 'connection', 'table_name', 'alias', 'joined_on', 'order']
        read_only_fields = ['id']


class DataSetFieldSerializer(serializers.ModelSerializer):
    source_table_name = serializers.SerializerMethodField()

    class Meta:
        model = DataSetField
        fields = [
            'id', 'dataset', 'name',
            'source_table', 'source_table_name',
            'source_column', 'expression', 'type',
            'aggregation', 'order'
        ]
        read_only_fields = ['id']

    def get_source_table_name(self, obj):
        return obj.source_table.table_name if obj.source_table else None


class DatasetSerializer(serializers.ModelSerializer):
    tables = DataSetTableSerializer(many=True, read_only=True)
    fields = DataSetFieldSerializer(many=True, read_only=True)

    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    file_source = serializers.PrimaryKeyRelatedField(
        queryset=FileUpload.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Dataset
        fields = [
            'id',
            'name',
            'description',
            'created_at',
            'owner',
            'connection',
            'file_source',
            'table_ref',
            'tables',
            'fields',
        ]
        read_only_fields = ['id', 'created_at', 'owner']
        
class FileUploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    # Добавляем swagger_schema_fields для корректной генерации схемы
    file = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Файл для загрузки"
    )

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
        swagger_schema_fields = {
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                    "description": "Файл для загрузки"
                }
            }
        }

    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None