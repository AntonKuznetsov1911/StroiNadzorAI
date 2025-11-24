"""
Celery Configuration для фоновых задач
Background tasks: PDF generation, Email sending, Analytics
"""

from celery import Celery
from celery.schedules import crontab
from config.settings import settings

# Создаем Celery app
celery_app = Celery(
    'stroinadzor',
    broker=settings.CELERY_BROKER_URL if hasattr(settings, 'CELERY_BROKER_URL') else 'redis://localhost:6379/1',
    backend=settings.CELERY_RESULT_BACKEND if hasattr(settings, 'CELERY_RESULT_BACKEND') else 'redis://localhost:6379/2'
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут максимум
    task_soft_time_limit=25 * 60,  # 25 минут soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Результаты хранятся 1 час
)

# Периодические задачи (Celery Beat)
celery_app.conf.beat_schedule = {
    'cleanup-old-cache': {
        'task': 'src.tasks.maintenance.cleanup_old_cache',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
    },
    'generate-daily-analytics': {
        'task': 'src.tasks.analytics.generate_daily_analytics',
        'schedule': crontab(hour=1, minute=0),  # Каждый день в 1:00
    },
    'send-daily-reports': {
        'task': 'src.tasks.reports.send_daily_reports',
        'schedule': crontab(hour=9, minute=0),  # Каждый день в 9:00
    },
    'update-metrics': {
        'task': 'src.tasks.monitoring.update_metrics',
        'schedule': 60.0,  # Каждую минуту
    },
}

# Автоматический поиск задач
celery_app.autodiscover_tasks(['src.tasks'])
