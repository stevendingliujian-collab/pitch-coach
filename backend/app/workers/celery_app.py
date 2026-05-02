from celery import Celery
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
)

celery_app.autodiscover_tasks(["app.workers"])
