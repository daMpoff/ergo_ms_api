from django.apps import AppConfig

class LmsCoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.lms.courses'
    label = 'lms_courses'