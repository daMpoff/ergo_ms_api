from django.db import migrations


def create_roles(apps, schema_editor):
	Role = apps.get_model('project_ed', 'Role')
	# Задаем фиксированные ID и названия
	roles = [
		(1, 'Администратор'),
		(2, 'Экспертная группа'),
		(3, 'Пользователь'),
	]
	for role_id, name in roles:
		# Обновляем, если запись с таким id уже существует, иначе создаем
		Role.objects.update_or_create(id=role_id, defaults={'name': name})


def delete_roles(apps, schema_editor):
	Role = apps.get_model('project_ed', 'Role')
	Role.objects.filter(id__in=[1, 2, 3]).delete()


class Migration(migrations.Migration):

	dependencies = [
		('project_ed', '0009_rename_projecteduserprofile_userprofile_and_more'),
	]

	operations = [
		migrations.RunPython(create_roles, delete_roles),
	]


