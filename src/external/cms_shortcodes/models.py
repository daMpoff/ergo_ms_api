from django.db import models
from django.contrib.auth.models import User

COMPONENT_TYPES = [
    ('button', 'Button'),
    ('container', 'Container'),
]

class CmsShortcodeTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES)  # Тип компонента (button, container и т.д.)
    class_list = models.JSONField(default=list, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)  # Например: {"text": "Купить", "icon": "cart"}
    is_active = models.BooleanField(default=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    date_of_creation = models.DateField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    position = models.PositiveIntegerField(default=0)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    content = models.TextField(blank=True, help_text='Опциональный HTML или текст')

    def __str__(self):
        return f"{self.name} ({self.component_type})"

    
class CmsPage(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)  # URL страницы
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    date_of_creation = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    
class CmsShortcodeInstance(models.Model):
    page = models.ForeignKey(CmsPage, on_delete=models.CASCADE, related_name='instances', db_index=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children', db_index=True)
    template = models.ForeignKey(CmsShortcodeTemplate, on_delete=models.PROTECT, help_text='Шаблон компонента')
    class_list = models.JSONField(default=list, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)
    date_of_creation = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        # При получении моделей, сортировка будет происходить по значению position
        ordering = ['position']
        # Уникальность позиции в пределах одного родителя
        constraints = [
            models.UniqueConstraint(fields=['parent', 'position'], name='unique_position_per_parent')
        ]

    def __str__(self):
        return f"{self.template.name} on {self.page.slug if self.page else 'внутри другого блока'}"


