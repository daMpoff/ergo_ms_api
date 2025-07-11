from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models

from src.modules.lms.models import (
    Test, Assignment, Resource, LessonItem, Lesson
)


class Command(BaseCommand):
    help = 'Миграция существующих тестов, заданий и ресурсов в модель LessonItem'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Выполнить без сохранения изменений в базу данных',
        )
        parser.add_argument(
            '--lesson-id',
            type=int,
            help='Мигрировать только указанный урок',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        lesson_id = options.get('lesson_id')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('РЕЖИМ ТЕСТИРОВАНИЯ: изменения не будут сохранены')
            )
        
        try:
            with transaction.atomic():
                stats = self.migrate_lesson_items(lesson_id)
                
                if dry_run:
                    raise Exception("Откат транзакции для режима тестирования")
                    
                self.print_migration_stats(stats)
                self.stdout.write(
                    self.style.SUCCESS(f'Миграция завершена успешно! Создано {stats["total"]} записей LessonItem')
                )
                
        except Exception as e:
            if dry_run and "Откат транзакции" in str(e):
                self.print_migration_stats(stats)
                self.stdout.write(
                    self.style.SUCCESS('ТЕСТИРОВАНИЕ ЗАВЕРШЕНО: изменения не были сохранены')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при миграции: {e}')
                )
                raise CommandError(f'Миграция не удалась: {e}')

    def migrate_lesson_items(self, specific_lesson_id=None):
        """Основная логика миграции"""
        stats = {
            'tests_migrated': 0,
            'assignments_migrated': 0,
            'resources_migrated': 0,
            'total': 0,
            'errors': []
        }
        
        # Получаем уроки для миграции
        if specific_lesson_id:
            lessons = Lesson.objects.filter(id=specific_lesson_id)
            if not lessons.exists():
                raise CommandError(f'Урок с ID {specific_lesson_id} не найден')
        else:
            lessons = Lesson.objects.all()
        
        for lesson in lessons:
            self.stdout.write(f'Обрабатываем урок: {lesson.name} (ID: {lesson.id})')
            
            # Миграция тестов
            lesson_stats = self.migrate_tests_for_lesson(lesson)
            stats['tests_migrated'] += lesson_stats['tests']
            
            # Миграция заданий
            lesson_stats = self.migrate_assignments_for_lesson(lesson)
            stats['assignments_migrated'] += lesson_stats['assignments']
            
            # Миграция ресурсов
            lesson_stats = self.migrate_resources_for_lesson(lesson)
            stats['resources_migrated'] += lesson_stats['resources']
        
        stats['total'] = (
            stats['tests_migrated'] + 
            stats['assignments_migrated'] + 
            stats['resources_migrated']
        )
        
        return stats

    def migrate_tests_for_lesson(self, lesson):
        """Миграция тестов для урока"""
        stats = {'tests': 0}
        
        # Получаем тесты урока, которые еще не имеют LessonItem
        tests = Test.objects.filter(lesson=lesson).exclude(
            lesson_items__isnull=False
        )
        
        for test in tests:
            try:
                # Получаем максимальный sort_order для урока
                max_order = LessonItem.objects.filter(lesson=lesson).aggregate(
                    max_order=models.Max('sort_order')
                )['max_order'] or 0
                
                # Создаем LessonItem
                lesson_item = LessonItem.objects.create(
                    lesson=lesson,
                    item_type='test',
                    test=test,
                    sort_order=max_order + 1
                )
                
                stats['tests'] += 1
                self.stdout.write(
                    f'  ✓ Создан LessonItem для теста: {test.title or test.name}'
                )
                
            except Exception as e:
                error_msg = f'Ошибка при создании LessonItem для теста {test.id}: {e}'
                self.stdout.write(self.style.ERROR(f'  ✗ {error_msg}'))
                
        return stats

    def migrate_assignments_for_lesson(self, lesson):
        """Миграция заданий для урока"""
        stats = {'assignments': 0}
        
        # Получаем задания урока, которые еще не имеют LessonItem
        assignments = Assignment.objects.filter(lesson=lesson).exclude(
            lesson_items__isnull=False
        )
        
        for assignment in assignments:
            try:
                # Получаем максимальный sort_order для урока
                max_order = LessonItem.objects.filter(lesson=lesson).aggregate(
                    max_order=models.Max('sort_order')
                )['max_order'] or 0
                
                # Создаем LessonItem
                lesson_item = LessonItem.objects.create(
                    lesson=lesson,
                    item_type='assignment',
                    assignment=assignment,
                    sort_order=max_order + 1
                )
                
                stats['assignments'] += 1
                self.stdout.write(
                    f'  ✓ Создан LessonItem для задания: {assignment.title}'
                )
                
            except Exception as e:
                error_msg = f'Ошибка при создании LessonItem для задания {assignment.id}: {e}'
                self.stdout.write(self.style.ERROR(f'  ✗ {error_msg}'))
                
        return stats

    def migrate_resources_for_lesson(self, lesson):
        """Миграция ресурсов для урока"""
        stats = {'resources': 0}
        
        # Получаем ресурсы урока, которые еще не имеют LessonItem
        resources = Resource.objects.filter(lesson=lesson).exclude(
            lesson_items__isnull=False
        )
        
        for resource in resources:
            try:
                # Получаем максимальный sort_order для урока
                max_order = LessonItem.objects.filter(lesson=lesson).aggregate(
                    max_order=models.Max('sort_order')
                )['max_order'] or 0
                
                # Создаем LessonItem
                lesson_item = LessonItem.objects.create(
                    lesson=lesson,
                    item_type='resource',
                    resource=resource,
                    sort_order=max_order + 1
                )
                
                stats['resources'] += 1
                self.stdout.write(
                    f'  ✓ Создан LessonItem для ресурса: {resource.name}'
                )
                
            except Exception as e:
                error_msg = f'Ошибка при создании LessonItem для ресурса {resource.id}: {e}'
                self.stdout.write(self.style.ERROR(f'  ✗ {error_msg}'))
                
        return stats

    def print_migration_stats(self, stats):
        """Вывод статистики миграции"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('СТАТИСТИКА МИГРАЦИИ:')
        self.stdout.write('='*50)
        self.stdout.write(f'Тестов мигрировано:     {stats["tests_migrated"]}')
        self.stdout.write(f'Заданий мигрировано:    {stats["assignments_migrated"]}')
        self.stdout.write(f'Ресурсов мигрировано:   {stats["resources_migrated"]}')
        self.stdout.write('-'*50)
        self.stdout.write(f'ВСЕГО записей создано:  {stats["total"]}')
        self.stdout.write('='*50) 