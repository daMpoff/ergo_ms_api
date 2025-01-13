import os

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Create a new submodule'

    def add_arguments(self, parser):
        parser.add_argument('module_name', type=str, help='The name of the module to create')
        parser.add_argument('submodule_name', type=str, help='The name of the submodule to create')

    def handle(self, *args, **options):
        submodule_name = options['submodule_name']
        module_name = options['module_name']

        submodule_path = os.path.join('main_module', submodule_name)

        if os.path.exists(submodule_path):
            raise CommandError(f'Submodule "{submodule_name}" already exists')

        os.makedirs(submodule_path)
        open(os.path.join(submodule_path, '__init__.py'), 'a').close()
        open(os.path.join(submodule_path, 'models.py'), 'a').close()
        open(os.path.join(submodule_path, 'views.py'), 'a').close()
        open(os.path.join(submodule_path, 'tests.py'), 'a').close()
        open(os.path.join(submodule_path, 'urls.py'), 'a').close()

        # Добавляем новый сабмодуль в urls.py основного модуля
        main_urls_path = os.path.join('main_module', 'urls.py')
        with open(main_urls_path, 'a') as main_urls_file:
            main_urls_file.write(f'\npath("{submodule_name}/", include("main_module.{submodule_name}.urls")),')

        self.stdout.write(self.style.SUCCESS(f'Successfully created submodule "{submodule_name}"'))
