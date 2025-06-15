from src.external.settings.models import Category, Tag
from src.external.settings.serializers import CategorySerializer, TagSerializer
from rest_framework import serializers
from .models import CmsPage, CmsShortcodeCategory, CmsShortcodeTemplate, CmsShortcodeInstance

class CmsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CmsShortcodeCategory
        fields = ['id', 'name']

class TemplateSerializer(serializers.ModelSerializer):
    component_type = serializers.SlugRelatedField(
        queryset= CmsShortcodeCategory.objects.all(),
        slug_field='name'
    )
    class Meta:
        model = CmsShortcodeTemplate
        fields = [
            'id',
            'name',
            'component_type',
            'class_list',
            'extra_data',
            'is_active',
            'icon_name',
            'allow_children'
        ]

class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class InstanceSerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    component_type = serializers.CharField(source='template.component_type.name', read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=CmsShortcodeInstance.objects.all(), allow_null=True, required=False)
    uid = serializers.CharField()
    class Meta:
        model = CmsShortcodeInstance
        fields = [
            'id',
            'template',
            'template_name',
            'component_type',
            'page',
            'parent',
            'class_list',
            'extra_data',
            'position',
            'children',
            'uid',
            'allow_children'
        ]

class PageSerializer(serializers.ModelSerializer):
    instances = InstanceSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False
    )
    tags = TagSerializer(many=True, read_only=True)
    tags_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, source='tags', write_only=True, required=False
    )

    class Meta:
        model = CmsPage
        fields = [
            'id', 'name', 'slug', 'category', 'category_id',
            'tags', 'tags_ids', 'is_homepage', 'instances'
        ]