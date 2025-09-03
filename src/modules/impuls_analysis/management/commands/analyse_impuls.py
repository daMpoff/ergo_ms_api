import os
import glob
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.files import File
from django.utils import timezone
from django.conf import settings

from src.modules.impuls_analysis.models import ImpulsAnalysis, ImpulsFile
from src.modules.impuls_analysis.tasks import process_excel_files


logger = logging.getLogger('impuls_analysis')


class Command(BaseCommand):
    help = (
        'Создаёт анализ импульса, прикрепляет Excel-файлы (расчет силы/план эксперимента) '
        'и запускает Celery-задачу обработки.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--user', required=False, default='1', help='ID пользователя (по умолчанию 1)')
        parser.add_argument('--title', required=True, help='Название анализа')
        parser.add_argument('--description', default='', help='Описание анализа')
        parser.add_argument('--force-file', dest='force_file', help='Имя файла "Расчет силы" в media/impuls_analysis/input_files')
        parser.add_argument('--plan-file', dest='plan_file', help='Имя файла "План эксперимента" в media/impuls_analysis/input_files')

    def handle(self, *args, **options):
        User = get_user_model()

        user_id = options.get('user') or '1'
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise CommandError('Некорректный параметр --user, ожидается целое число')
        title = options['title']
        description = options.get('description') or ''
        force_name = options.get('force_file')
        plan_name = options.get('plan_file')

        input_dir = os.path.join(settings.MEDIA_ROOT, 'impuls_analysis', 'input_files')
        if not os.path.isdir(input_dir):
            raise CommandError(f'Директория с входными файлами не найдена: {input_dir}')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'Пользователь с id={user_id} не найден')

        analysis = ImpulsAnalysis.objects.create(
            user=user,
            title=title,
            description=description,
            status='pending',
            analysis_type='standard',
            created_at=timezone.now(),
        )

        created_types = []

        def resolve_path(name_or_none: str, patterns: list[str]) -> str | None:
            # Если указано имя файла — берём его из input_dir
            if name_or_none:
                candidate = os.path.join(input_dir, name_or_none)
                return candidate
            # Иначе пытаемся найти самый новый файл по наборам масок
            matches: list[str] = []
            for p in patterns:
                matches.extend(glob.glob(os.path.join(input_dir, p)))
            # Отфильтровываем временные Excel файлы (~$...)
            matches = [m for m in matches if not os.path.basename(m).startswith('~$')]
            if not matches:
                return None
            # Берём самый новый по времени модификации
            return max(matches, key=os.path.getmtime)

        def attach_file(path: str, file_type: str):
            if not path:
                return
            if not os.path.exists(path):
                raise CommandError(f'Файл не найден: {path}')
            with open(path, 'rb') as f:
                django_file = File(f, name=os.path.basename(path))
                ImpulsFile.objects.create(
                    analysis=analysis,
                    file_type=file_type,
                    original_filename=os.path.basename(path),
                    file=django_file,
                    file_size=os.path.getsize(path),
                )
            created_types.append(file_type)

        try:
            force_path_resolved = resolve_path(force_name, ['*Расчет силы*.xlsx', '*расчет силы*.xlsx'])
            plan_path_resolved = resolve_path(plan_name, ['*План экспер*.xlsx', '*план экспер*.xlsx'])

            if not force_path_resolved and not plan_path_resolved:
                raise CommandError('Не найден ни один входной файл в media/impuls_analysis/input_files')

            attach_file(force_path_resolved, 'force_calculation')
            attach_file(plan_path_resolved, 'experiment_plan')
        except CommandError:
            # если ошибка на аттаче файла — удалим черновик анализа
            analysis.delete()
            raise

        logger.info(
            f'Создан анализ {analysis.id} для пользователя {user_id}. Прикреплены файлы: {created_types}'
        )

        # Запускаем Celery обработку
        process_excel_files.delay(str(analysis.id))

        self.stdout.write(self.style.SUCCESS(
            f'Анализ создан: {analysis.id}. Запущена обработка файлов Celery.'
        ))


