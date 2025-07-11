from django.apps import AppConfig

class LmsUsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.lms.users'
    label = 'lms_users'