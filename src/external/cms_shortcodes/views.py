from django.db import models
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import CmsPage, CmsShortcodeTemplate, CmsShortcodeInstance
from .serializers import PageSerializer, TemplateSerializer, InstanceSerializer

class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CmsShortcodeTemplate.objects.filter(is_active=True)
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]

class PageViewSet(viewsets.ModelViewSet):
    queryset = CmsPage.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

class InstanceViewSet(viewsets.ModelViewSet):
    queryset = CmsShortcodeInstance.objects.all()
    serializer_class = InstanceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        parent_id = self.request.data.get('parent')
        page_id = self.request.data.get('page')

        if 'position' not in self.request.data:
            siblings = CmsShortcodeInstance.objects.filter(
                parent=parent_id, page=page_id
            )
            max_pos = siblings.aggregate(models.Max('position'))['position__max'] or 0
            serializer.save(
                position=max_pos + 1,
                parent_id=parent_id,
                page_id=page_id
            )
        else:
            serializer.save(
                parent_id=parent_id,
                page_id=page_id
            )