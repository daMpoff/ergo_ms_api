from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('project_ed', '0013_sync_user_profiles'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='role',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='position',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='faculty',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='department',
        ),
    ]


