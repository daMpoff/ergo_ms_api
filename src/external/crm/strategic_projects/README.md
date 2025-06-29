# Модуль управления стратегическими проектами

## Описание

Модуль управления стратегическими проектами (СтрПр) - это подмодуль CRM системы АС ПД, предназначенный для создания, сопровождения, утверждения, реализации и архивирования стратегических проектов организации.

## Основные возможности

- Импорт программы развития из CSV файлов
- Создание проектов на основе тем программы развития
- Многоэтапный процесс утверждения проектов
- Управление этапами и исполнителями проектов
- Создание отчетов и прикрепление результатов
- Контроль сроков и бюджета проектов
- История изменений по каждому проекту

## Установка и настройка

### 1. Применение миграций Django

```bash
cd api
.venv/scripts/activate
cd src
python manage.py makemigrations strategic_projects
python manage.py migrate
```

### 2. Создание ролей пользователей

В системе предусмотрены следующие роли:
- `strategic_admin` - Администратор СтрПр
- `strategic_curator` - Куратор СтрПр
- `expert_group` - Член экспертной группы
- `expert_group_leader` - Руководитель экспертной группы
- `project_leader` - Руководитель проекта (ППС)

## API Endpoints

### Программы развития
- `GET /api/crm/strategic-projects/development-programs/` - список программ
- `POST /api/crm/strategic-projects/development-programs/import_program/` - импорт программы

### Темы программы
- `GET /api/crm/strategic-projects/program-topics/` - список тем
- `POST /api/crm/strategic-projects/program-topics/{id}/reserve_and_create_project/` - создание проекта

### Стратегические проекты
- `GET /api/crm/strategic-projects/strategic-projects/` - список проектов
- `POST /api/crm/strategic-projects/strategic-projects/` - создание проекта
- `GET /api/crm/strategic-projects/strategic-projects/{id}/` - детали проекта
- `PATCH /api/crm/strategic-projects/strategic-projects/{id}/` - обновление проекта
- `POST /api/crm/strategic-projects/strategic-projects/{id}/submit_for_approval/` - отправка на утверждение
- `POST /api/crm/strategic-projects/strategic-projects/{id}/approve/` - утверждение
- `POST /api/crm/strategic-projects/strategic-projects/{id}/reject/` - отклонение
- `POST /api/crm/strategic-projects/strategic-projects/{id}/start_project/` - запуск проекта
- `POST /api/crm/strategic-projects/strategic-projects/{id}/complete_project/` - завершение проекта

### Этапы проектов
- `GET /api/crm/strategic-projects/project-stages/` - список этапов
- `POST /api/crm/strategic-projects/project-stages/{id}/start_stage/` - начало этапа
- `POST /api/crm/strategic-projects/project-stages/{id}/complete_stage/` - завершение этапа

### Отчеты
- `GET /api/crm/strategic-projects/project-reports/` - список отчетов
- `POST /api/crm/strategic-projects/project-reports/` - создание отчета
- `POST /api/crm/strategic-projects/project-reports/{id}/submit_for_approval/` - отправка на согласование
- `POST /api/crm/strategic-projects/project-reports/{id}/approve_report/` - согласование отчета

## Пример CSV файла для импорта

См. файл `sample_development_program.csv` в этой директории. 