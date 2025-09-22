from django.db import migrations


FACULTIES = [
	('Учебно-научный технологический институт', 'УНТИ'),
	('Учебно-научный институт транспорта', 'УНИТ'),
	('Факультет информационных технологий', 'ФИТ'),
	('Факультет отраслевой и цифровой экономики', 'ФОЦЭ'),
	('Факультет энергетики и электроники', 'ФЭЭ'),
	('Механико-технологический факультет', 'МТФ'),
]


def create_faculties(apps, schema_editor):
	Faculty = apps.get_model('project_ed', 'Faculty')
	for name, short in FACULTIES:
		Faculty.objects.update_or_create(
			name=name,
			defaults={'short_name': short},
		)


def delete_faculties(apps, schema_editor):
	Faculty = apps.get_model('project_ed', 'Faculty')
	Faculty.objects.filter(name__in=[name for name, _ in FACULTIES]).delete()


class Migration(migrations.Migration):

	dependencies = [
		('project_ed', '0011_add_short_name_to_faculty_and_department'),
	]

	operations = [
		migrations.RunPython(create_faculties, delete_faculties),
	]


