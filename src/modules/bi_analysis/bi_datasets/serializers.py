from rest_framework import serializers
from django.contrib.auth import get_user_model

from src.modules.bi_analysis.bi_connections.models import Connection
from src.modules.bi_analysis.bi_datasets.models import FileUpload, Dataset, DataSetTable, DataSetField

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
            'file_upload_id', 'file_upload_name', 'columns_info',
            'joined_on_type', 'joined_on_left', 'joined_on_right'
        ]
        read_only_fields = ['id']
        
    def get_table_ref(self, obj):
        return obj.table_name
    
    def get_display_name(self, obj):
        if obj.display_name and not obj.display_name.startswith('temp_'):
            return obj.display_name

        if obj.file_upload and obj.sheet_name:
            filename = obj.file_upload.original_filename.replace('.xlsx', '')
            return f"{filename} – {obj.sheet_name}"
        elif obj.file_upload:
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
            'aggregation', 'order', 'description'
        ]
        read_only_fields = ['id', 'source_table',
        'source_column', 'expression', 'order', 'source_table_name']

    def get_source_table_name(self, obj):
        return obj.source_table.table_name if obj.source_table else None

class DatasetUpdateSerializer(serializers.ModelSerializer):
    fields = DataSetFieldSerializer(many=True, required=False)

    class Meta:
        model  = Dataset
        fields = ['id', 'name', 'description', "connection", 'fields']
        read_only_fields = ['id', 'connection']

    def update(self, instance, validated_data):
        instance = super().update(instance, {k: v for k, v in validated_data.items() if k != 'fields'})
        fields_data = self.initial_data.get('fields', [])
        if fields_data:
            for field_data in fields_data:
                field_obj = instance.fields.filter(id=field_data.get('id')).first()
                if field_obj:
                    for attr in ['name', 'aggregation', 'type', 'description']:
                        if attr in field_data:
                            setattr(field_obj, attr, field_data[attr])
                    field_obj.save(update_fields=['name', 'aggregation', 'type', 'description'])
        return instance
    
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
    tables  = DataSetTableSerializer(many=True, read_only=True)
    fields  = DataSetFieldSerializer(many=True, read_only=True)
    class Meta:
        model  = Dataset
        fields = '__all__'

# --- Для списка (list) ---
class DatasetShortSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    storage_type   = serializers.SerializerMethodField()

    def get_storage_type(self, obj):
        return 'postgres'

    class Meta:
        model  = Dataset
        fields = ['id', 'name', 'owner_username',
                  'storage_type', 'created_at']

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