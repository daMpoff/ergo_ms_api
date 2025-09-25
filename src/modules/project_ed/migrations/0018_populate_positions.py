from django.db import migrations


def create_positions(apps, schema_editor):
    Position = apps.get_model('project_ed', 'Position')
    # Список должностей для добавления
    positions = [
        'Ассистент',
        'Преподаватель',
        'Ст. преподаватель',
        'Доцент',
        'Профессор',
        'Декан',
        'Директор',
        'Зав. кафедрой',
        'Проректор',
        'Ректор',
    ]
    
    for position_name in positions:
        # Создаем должность, если она еще не существует
        Position.objects.get_or_create(name=position_name)


def delete_positions(apps, schema_editor):
    Position = apps.get_model('project_ed', 'Position')
    # Удаляем добавленные должности
    positions_to_delete = [
        'Ассистент',
        'Преподаватель',
        'Ст. преподаватель',
        'Доцент',
        'Профессор',
        'Декан',
        'Директор',
        'Зав. кафедрой',
        'Проректор',
        'Ректор',
    ]
    Position.objects.filter(name__in=positions_to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('project_ed', '0017_remove_targetindicator_current_value_and_more'),
    ]

    operations = [
        migrations.RunPython(create_positions, delete_positions),
    ]
