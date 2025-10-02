# Generated manually for populating ProjectRole with basic roles

from django.db import migrations


def populate_project_roles(apps, schema_editor):
    """Заполняем справочник ролей проекта основными ролями."""
    ProjectRole = apps.get_model('project_ed_projects', 'ProjectRole')
    
    roles = [
        'Руководитель',
        'Куратор', 
        'Заказчик',
        'Исполнитель',
    ]
    
    for role_name in roles:
        ProjectRole.objects.get_or_create(name=role_name)


def reverse_populate_project_roles(apps, schema_editor):
    """Обратная миграция - удаляем созданные роли."""
    ProjectRole = apps.get_model('project_ed_projects', 'ProjectRole')
    
    roles = [
        'Руководитель',
        'Куратор', 
        'Заказчик',
        'Исполнитель',
    ]
    
    ProjectRole.objects.filter(name__in=roles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('project_ed_projects', '0002_projectrole_projectuserrole'),
    ]

    operations = [
        migrations.RunPython(
            populate_project_roles,
            reverse_populate_project_roles
        ),
    ]
