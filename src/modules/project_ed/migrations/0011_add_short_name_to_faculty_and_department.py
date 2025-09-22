from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('project_ed', '0010_populate_roles'),
	]

	operations = [
		migrations.AddField(
			model_name='faculty',
			name='short_name',
			field=models.CharField(blank=True, default='', max_length=10, verbose_name='Сокращённое название'),
		),
		migrations.AddField(
			model_name='department',
			name='short_name',
			field=models.CharField(blank=True, default='', max_length=10, verbose_name='Сокращённое название'),
		),
	]


