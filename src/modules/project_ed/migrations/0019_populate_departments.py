from django.db import migrations


DEPARTMENTS = [
    ("Машиностроение и материаловедение", "МиМ", "МТФ"),
    ("Управление качеством, стандартизация и метрология", "УКСиМ", "МТФ"),
    ("Техносферная безопасность", "ТБ", "МТФ"),
    ("Физическое воспитание и спорт", "ФВиС", "МТФ"),
    ("Автоматизированные технологические системы", "АТС", "УНТИ"),
    ("Металлорежущие станки и инструменты", "МСиИ", "УНТИ"),
    ("Технология машиностроения", "ТМ", "УНТИ"),
    ("Производство и сервис в транспортном машиностроении", "ПСТМ", "УНИТ"),
    ("Высокотехнологичное транспортное машиностроение", "ВТМ", "УНИТ"),
    ("Турбиностроение и трубопроводные транспортные системы", "ТиТТС", "ФЭЭ"),
    ("Электро-и теплоэнергетика", "ЭТЭ", "ФЭЭ"),
    ("Дизайн и проектирование в машиностроении", "ДПМ", "УНИТ"),
    ("Электронные, радиоэлектронные и электротехнические системы", "ЭРЭиЭС", "ФЭЭ"),
    ("Общая физика", "ОФ", "ФЭЭ"),
    ("Гуманитарные и социальные дисциплины", "ГиСД", "ФОЦЭ"),
    ("Отраслевая экономика и управление", "ОЭУ", "ФОЦЭ"),
    ("Информатика и программное обеспечение", "ИиПО", "ФИТ"),
    ("Компьютерные технологии и системы", "КТС", "ФИТ"),
    ("Системы информационной безопасности", "СИБ", "ФИТ"),
    ("Высшая математика", "ВМ", "ФИТ"),
    ("Иностранные языки", "Ин. Яз.", "ФОЦЭ"),
    ("Цифровая экономика", "ЦЭ", "ФОЦЭ"),
]


def create_departments(apps, schema_editor):
    Faculty = apps.get_model('project_ed', 'Faculty')
    Department = apps.get_model('project_ed', 'Department')

    for full_name, short_name, faculty_short in DEPARTMENTS:
        faculty = Faculty.objects.filter(short_name=faculty_short).first()
        if faculty is None:
            raise ValueError(f"Не найден факультет с short_name='{faculty_short}' для кафедры '{full_name}'")

        Department.objects.update_or_create(
            name=full_name,
            defaults={
                'short_name': short_name,
                'faculty': faculty,
            },
        )


def delete_departments(apps, schema_editor):
    Department = apps.get_model('project_ed', 'Department')
    names = [name for name, _short, _fac in DEPARTMENTS]
    Department.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('project_ed', '0018_populate_positions'),
    ]

    operations = [
        migrations.RunPython(create_departments, delete_departments),
    ]


