import os

from celery import Celery
from celery.schedules import timedelta

from django.conf import settings

from src.core.utils.auto_api.auto_config import get_env_deploy_type

deploy_type = get_env_deploy_type()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', deploy_type)

app = Celery('src')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.update(
    beat_schedule_filename="celery/celerybeat-schedule",
)

# Настройка периодических задач
app.conf.beat_schedule = {
    'monitor-redis-status': {
        'task': 'src.core.utils.tasks.monitor_redis_status',
        'schedule': timedelta(seconds=10),
    },
}