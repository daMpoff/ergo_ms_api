from rest_framework import serializers
from .models import CmsPage, CmsShortcodeTemplate, CmsShortcodeInstance

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CmsShortcodeTemplate
        fields = [
            'id',
            'name',
            'component_type',
            'class_list',
            'extra_data',
            'is_active',
            'icon_name'
        ]

class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class InstanceSerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    component_type = serializers.CharField(source='template.component_type', read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=CmsShortcodeInstance.objects.all(), allow_null=True, required=False)

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
            'children'
        ]

class PageSerializer(serializers.ModelSerializer):
    instances = InstanceSerializer(many=True, read_only=True)

    class Meta:
        model = CmsPage
        fields = [
            'id',
            'name',
            'slug',
            'instances'
        ]