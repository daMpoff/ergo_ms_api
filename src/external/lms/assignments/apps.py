from django.apps import AppConfig

class LmsAssignmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.external.lms.assignments'
    label = 'lms_assignments'