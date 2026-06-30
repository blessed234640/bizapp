import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "bizapp",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.check_deadlines",
        "tasks.daily_report",
    ],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

celery.conf.beat_schedule = {
    "check-overdue-tasks": {
        "task": "tasks.check_deadlines.check_overdue_tasks",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "generate-daily-reports": {
        "task": "tasks.daily_report.generate_all_reports",
        "schedule": crontab(minute=0, hour=15),
    },
}
