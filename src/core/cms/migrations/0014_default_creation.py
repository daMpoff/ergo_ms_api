from django.db import migrations
from django.contrib.contenttypes.models import ContentType
from src.core.cms.models import CMSPage
import os
import re
def create_default_data(apps, schema_editor):
    PermissionMark = apps.get_model('cms', 'PermissionMark')
    permission_marks = [
        {'name': 'ComponentAccessionToRead', 'id': 1},
        {'name': 'ComponentAccessionToReadAndWrite', 'id': 2},
        {'name': 'PageAccession', 'id': 3},
        {'name': 'AdminAccession', 'id': 4},
    ]    
    for mark_data in permission_marks:
        PermissionMark.objects.get_or_create(
            id=mark_data['id'],
            defaults={'name': mark_data['name']}
        )
    paths = []
    path =(os.getcwd().replace('\\','/')).replace('/api','/client/src/js/routers.js')
    with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    const_pattern = r'const\s+(\w+Routes?)\s*='
                    route_constants = re.findall(const_pattern, content)
                    route_constants = [const for const in route_constants if (const != 'mainRoutes')& (const!= 'adminpanelRoutes')
                        & (const!= 'userRoutes') & (const!='settingsRoutes') &(const!= 'startRoutes')]
                    for const_name in route_constants:
                        const_pattern = f"const {const_name} = \[(.*?)\]"
                        const_match = re.search(const_pattern, content, re.DOTALL)
                        content_const = const_match.group(1)
                        const_pattern = f"path: '(.*?)'"
                        mainpath = re.search(const_pattern,content_const).group(1)
                        const_pattern = r'children:(.*)'
                        children = re.search(const_pattern, content_const, re.DOTALL)
                        if children:
                            const_pattern = f"path: '(.*?)'"
                            paths1 = re.findall(const_pattern,children.group(1))
                            for p in paths1:
                                paths.append(mainpath+'/'+p)
                            
                        else:
                            const_pattern =f"path: '(.*?)'"
                            mainpathes = re.findall(const_pattern,content_const)
                            for mainp in mainpathes:
                                paths.append(mainp)
    for p in paths:
        CMSPage.objects.get_or_create(path = p)
class Migration(migrations.Migration):
    dependencies = [
        ('cms', '0013_alter_accession_component_id'),
    ]

    operations = [
        migrations.RunPython(create_default_data),
    ]