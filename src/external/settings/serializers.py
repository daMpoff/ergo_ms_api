from rest_framework import serializers
from .models import UploadedFile
from .models import Category
from .models import Tag
from .models import UserAvatar
from .models import (
    GeneralSettings, AppearanceSettings,
    SecuritySettings, MediaSettings, PermalinkSettings, EmailSettings
)
class UploadedFileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ['id', 'file', 'name', 'size', 'url', 'uploaded_at']

    def get_name(self, obj):
        return obj.file.name.split('/')[-1]

    def get_size(self, obj):
        return obj.file.size
    
    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file:
            url = obj.file.url
            if request is not None:
                url = request.build_absolute_uri(url)
            return url
        return ""
class GeneralSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralSettings
        fields = '__all__'

class AppearanceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppearanceSettings
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
class UploadedFileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    alt_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UploadedFile
        fields = ['id', 'file', 'name', 'size', 'alt_name', 'uploaded_at']

    def get_name(self, obj):
        return obj.file.name.split('/')[-1]

    def get_size(self, obj):
        return obj.file.size
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'slug']
        read_only_fields = ['slug']
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['slug'] = instance.slug
        return ret
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'category']
class UserAvatarSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = UserAvatar
        fields = ['id', 'user', 'image', 'uploaded_at']


