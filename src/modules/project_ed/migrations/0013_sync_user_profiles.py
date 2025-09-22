from django.conf import settings
from django.db import migrations


def create_or_update_user_profiles(apps, schema_editor):
	# Получаем модели с исторического реестра
	UserProfile = apps.get_model('project_ed', 'UserProfile')
	Role = apps.get_model('project_ed', 'Role')
	user_app_label, user_model_name = settings.AUTH_USER_MODEL.split('.')
	User = apps.get_model(user_app_label, user_model_name)

	# Получаем роль "Пользователь" (предполагается, что создана в 0010)
	role_user = None
	try:
		role_user = Role.objects.get(id=3)
	except Role.DoesNotExist:
		# Фолбэк по имени
		role_user, _ = Role.objects.get_or_create(name='Пользователь')

	# Проходим по всем пользователям и создаем профиль при его отсутствии
	for user in User.objects.all().only('id'):
		profile, created = UserProfile.objects.get_or_create(user_id=user.id)
		# Если у профиля не установлена роль, задаем ее через ссылочное поле
		if not profile.role_ref_id:
			profile.role_ref_id = role_user.id
			profile.save(update_fields=['role_ref', 'updated_at'])


def reverse_noop(apps, schema_editor):
	# Специально не удаляем профили при откате, чтобы не терять данные
	pass


class Migration(migrations.Migration):

	dependencies = [
		('project_ed', '0012_populate_faculties'),
		('lms', '0001_initial'),
	]

	operations = [
		migrations.RunPython(create_or_update_user_profiles, reverse_noop),
	]


