from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pitch_coach",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.generate_plan_task": {"queue": "plan"},
        "app.workers.tasks.score_rehearsal_task": {"queue": "scoring"},
    },
    # Periodic tasks
    beat_schedule={
        # Reset monthly usage counters at 00:00 on the 1st of every month
        "reset-monthly-usage": {
            "task": "app.workers.tasks.reset_monthly_usage_task",
            "schedule": crontab(hour=0, minute=0, day_of_month=1),
        },
        # Warn users 48h before bid date (runs every hour)
        "bid-deadline-warning": {
            "task": "app.workers.tasks.bid_deadline_warning_task",
            "schedule": crontab(minute=0),  # every hour
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
