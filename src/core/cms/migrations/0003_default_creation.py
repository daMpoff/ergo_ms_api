from django.db import migrations

from src.core.cms.scripts import create_default_data

class Migration(migrations.Migration):
    dependencies = [
        ('cms', '0002_cmspage_alter_groupurl_options_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_data),
    ]