import redis
from backend.app.core.config import settings

def get_redis_client():
    return redis.Redis.from_url(settings.REDIS_URL)

def acquire_project_lock(project_id: str, expire_seconds: int = 3600) -> bool:
    """Acquires a lock for a project to prevent duplicate executions."""
    try:
        r = get_redis_client()
        lock_key = f"lock:project:{project_id}"
        # Set if not exists with an expiry
        return bool(r.set(lock_key, "locked", ex=expire_seconds, nx=True))
    except Exception as e:
        print(f"Redis lock acquisition error: {e}")
        # In case Redis is down, we fallback to allowing execution but logging warning
        return True

def release_project_lock(project_id: str):
    """Releases a project lock."""
    try:
        r = get_redis_client()
        lock_key = f"lock:project:{project_id}"
        r.delete(lock_key)
    except Exception as e:
        print(f"Redis lock release error: {e}")
