import socket
from urllib.parse import urlparse
from celery import Celery
from celery.schedules import crontab
from backend.app.core.config import settings

def is_redis_available(redis_url: str) -> bool:
    """Check if Redis server is reachable on the network."""
    try:
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=1):
            return True
    except Exception:
        return False

redis_online = is_redis_available(settings.REDIS_URL)

if redis_online:
    broker_url = settings.REDIS_URL
    result_backend = settings.REDIS_URL
    always_eager = False
    print(f"Celery: Connected to Redis broker at {settings.REDIS_URL}")
else:
    broker_url = "memory://"
    result_backend = "cache+memory://"
    always_eager = True
    print("Celery Notice: Redis server not detected on host. Falling back to in-memory broker (task_always_eager=True).")

celery_app = Celery(
    "youtube_empire_worker",
    broker=broker_url,
    backend=result_backend,
    include=["backend.app.tasks.workflow_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_always_eager=always_eager,
    # Celery Beat Schedule for automated recurring tasks
    beat_schedule={
        "daily-trend-hunt": {
            "task": "tasks.hunt_trends",
            "schedule": crontab(hour=6, minute=0),  # Every day at 06:00 UTC
            "options": {"queue": "default"},
        },
        "daily-analytics-sync": {
            "task": "tasks.sync_youtube_analytics",
            "schedule": crontab(hour=8, minute=0),  # Every day at 08:00 UTC
            "options": {"queue": "default"},
        },
    }
)

