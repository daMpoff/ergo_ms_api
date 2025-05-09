from rest_framework import serializers
from .models import UploadedFile
from .models import (
    GeneralSettings, AppearanceSettings, SEOSettings,
    SecuritySettings, MediaSettings, PermalinkSettings, EmailSettings
)
class UploadedFileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ['id', 'file', 'name', 'size', 'uploaded_at']

    def get_name(self, obj):
        return obj.file.name.split('/')[-1]

    def get_size(self, obj):
        return obj.file.size
class GeneralSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralSettings
        fields = '__all__'

class AppearanceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppearanceSettings
        fields = '__all__'

class SEOSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SEOSettings
        fields = '__all__'

class SecuritySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySettings
        fields = '__all__'

class MediaSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaSettings
        fields = '__all__'

class PermalinkSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermalinkSettings
        fields = '__all__'

class EmailSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSettings
        fields = '__all__'
