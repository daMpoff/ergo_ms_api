from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FileUpload, Dataset, DataSetTable, DataSetField
import os
import pandas as pd
import openpyxl, csv

User = get_user_model()

# --- Короткие сериализаторы для списков/превью ---
class DataSetTableShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSetTable
        fields = ['id', 'table_name', 'alias']

class DataSetFieldShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSetField
        fields = ['id', 'name']

# --- Полные сериализаторы для detail ---
class DataSetTableSerializer(serializers.ModelSerializer):
    table_ref = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    file_upload_id = serializers.SerializerMethodField()
    file_upload_name = serializers.SerializerMethodField()
    joined_on = serializers.SerializerMethodField()
    joined_on_type = serializers.CharField()
    joined_on_left = serializers.CharField()
    joined_on_right = serializers.CharField()

    class Meta:
        model = DataSetTable
        fields = [
            'id', 'dataset', 'connection', 'table_name', 'alias',
            'joined_on', 'order', 'table_ref', 'display_name',
            'file_upload_id', 'file_upload_name',
            'joined_on_type', 'joined_on_left', 'joined_on_right'
        ]
        read_only_fields = ['id']
        
    def get_table_ref(self, obj):
        return obj.table_name
    
    def get_display_name(self, obj):
        # Всегда через file_upload, если есть
        if getattr(obj, 'file_upload', None) and getattr(obj, 'sheet_name', None):
            filename = obj.file_upload.original_filename
            filename = filename.replace('.xlsx', '')
            return f"{filename} – {obj.sheet_name}"
        elif getattr(obj, 'file_upload', None):
            return obj.file_upload.original_filename
        else:
            return obj.table_name

    def get_file_upload_id(self, obj):
        return obj.file_upload.id if obj.file_upload else None

    def get_file_upload_name(self, obj):
        return obj.file_upload.original_filename if obj.file_upload else None

    def get_joined_on(self, obj):
        if obj.joined_on_type:
            return {
                "type": obj.joined_on_type,
                "left_column": obj.joined_on_left,
                "right_column": obj.joined_on_right,
            }
        return None

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
    
class DatasetDetailSerializer(serializers.ModelSerializer):
    tables = DataSetTableSerializer(many=True, read_only=True)
    fields = DataSetFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Dataset
        fields = [
            'id',
            'name',
            'description',
            'created_at',
            'tables',
            'fields',
        ]

# --- Detail сериализаторы ---
class DatasetDetailFullSerializer(serializers.ModelSerializer):
    tables = DataSetTableSerializer(many=True, read_only=True)
    fields = DataSetFieldSerializer(many=True, read_only=True)
    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'created_at',
            'tables', 'fields',
        ]

# --- Для списка (list) ---
class DatasetShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ['id', 'name', 'description', 'created_at']

# --- Для create/update ---
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

# --- File upload сериализатор ---
class FileUploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FileUpload
        fields = [
            'id', 'name', 'file', 'file_url', 'uploaded_at',
            'owner', 'original_filename', 'file_type', 'connection', 'columns_info'
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