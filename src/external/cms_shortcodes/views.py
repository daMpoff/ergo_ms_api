from uuid import uuid4
from django.db import models
from src.external.settings.models import Category
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import generics, permissions
from .models import CmsPage, CmsShortcodeCategory, CmsShortcodeTemplate, CmsShortcodeInstance, SiteLayout
from .serializers import CmsCategorySerializer, PageSerializer, SiteLayoutSerializer, TemplateSerializer, InstanceSerializer

class ShortcodeCategoryViewSet(viewsets.ModelViewSet):
    queryset = CmsShortcodeCategory.objects.all()
    serializer_class = CmsCategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

class TemplateViewSet(viewsets.ModelViewSet):
    queryset = CmsShortcodeTemplate.objects.all()
    serializer_class = TemplateSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

class PageViewSet(viewsets.ModelViewSet):
    queryset = CmsPage.objects.all()
    serializer_class = PageSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        page = serializer.save(creator=self.request.user)
        layout = SiteLayout.objects.first()
        blocks = []
        if layout and layout.header_template:
            blocks.append(CmsShortcodeInstance(
                page=page, template=layout.header_template, uid=uuid4().hex, position=0
            ))
        if layout and layout.footer_template:
            blocks.append(CmsShortcodeInstance(
                page=page, template=layout.footer_template, uid=uuid4().hex, position=9999
            ))
        if blocks:
            CmsShortcodeInstance.objects.bulk_create(blocks)

class PageByFullPathView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema( ... )
    def get(self, request):
        path = request.query_params.get('full_path', '').strip('/')
        if path == '':
            # корневая «домашняя» категория
            page = CmsPage.objects.filter(category=None, category_index=True).first()
            if page:
                return Response(PageSerializer(page).data)
            return Response({'detail': 'Страница не найдена'}, status=404)

        parts      = path.split('/')
        slug_part  = parts[-1]
        cat_slugs  = parts[:-1]

        # ищем обычную страницу со slug-ом ─ как раньше
        parent = None
        for s in cat_slugs:
            parent = Category.objects.filter(slug=s, parent=parent).first()
            if not parent:
                break
        if parent is not None:
            page = CmsPage.objects.filter(slug=slug_part, category=parent).first()
            if page:
                return Response(PageSerializer(page).data)

        # если не нашли — может это индекс-страница категории
        parent = None
        for s in parts:                         # используем ВЕСЬ путь
            parent = Category.objects.filter(slug=s, parent=parent).first()
            if not parent:
                return Response({'detail': f'Категория не найдена: {s}'}, status=404)

        page = CmsPage.objects.filter(category=parent, category_index=True).first()
        if page:
            return Response(PageSerializer(page).data)

        return Response({'detail': 'Страница не найдена'}, status=404)

class InstanceViewSet(viewsets.ModelViewSet):
    queryset = CmsShortcodeInstance.objects.all()
    serializer_class = InstanceSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'tree']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='tree', permission_classes=[AllowAny])
    def tree(self, request):
        page_id = request.query_params.get('page')
        if not page_id:
            return Response({'detail': 'Необходим id страницы'}, status=400)
        roots = CmsShortcodeInstance.objects.filter(page_id=page_id, parent=None)
        serializer = self.get_serializer(roots, many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=['post'], url_path='bulk_create', permission_classes=[IsAuthenticated])
    def bulk_create(self, request):
        """
        Сохраняет полное дерево инстансов для страницы.
        Ожидает flat-массив с полями: uid, parent (uid), page, template, position, ...
        """
        data = request.data
        if not data or not isinstance(data, list):
            return Response({'detail': 'Должен быть передан список'}, status=400)

        page_id = data[0].get('page')
        if not page_id:
            return Response({'detail': 'Нет page id в первом элементе'}, status=400)

        # 1. Удалить старое дерево этой страницы
        CmsShortcodeInstance.objects.filter(page_id=page_id).delete()

        # 2. Создать все инстансы без parent, сопоставить их по uid
        uid_to_dbid = {}
        instances = []
        for item in data:
            instance = CmsShortcodeInstance.objects.create(
                template_id=item['template'],
                class_list=item.get('class_list', []),
                extra_data=item.get('extra_data', {}),
                page_id=page_id,
                position=item.get('position', 0),
                uid=item.get('uid'),
                # parent — пока не указываем
                # любые доп.поля аналогично (например, is_active, icon_name и т.д.)
                is_active=item.get('is_active', True),
                icon_name=item.get('icon_name'),
                allow_children=item.get('allow_children', False),
                # ... другие поля по необходимости
            )
            uid_to_dbid[item['uid']] = instance.id
            instances.append((instance, item.get('parent')))

        # 3. Второй проход — установить parent_id там, где надо
        for instance, parent_uid in instances:
            if parent_uid:
                parent_id = uid_to_dbid.get(parent_uid)
                if parent_id:
                    instance.parent_id = parent_id
                    instance.save(update_fields=['parent'])

        # 4. Вернуть новое дерево для фронта (опционально)
        instances = CmsShortcodeInstance.objects.filter(page_id=page_id)
        serializer = self.get_serializer(instances, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class SiteLayoutViewSet(viewsets.ModelViewSet):
    queryset = SiteLayout.objects.all()
    serializer_class = SiteLayoutSerializer

    def get_queryset(self):
        return SiteLayout.objects.filter(pk=1)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
class SiteLayoutView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class   = SiteLayoutSerializer
    queryset           = SiteLayout.objects.all()

    def get_object(self):
        obj, _ = SiteLayout.objects.get_or_create(pk=1)
        return obj
