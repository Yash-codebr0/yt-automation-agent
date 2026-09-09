from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.services.youtube_service import YouTubeService

router = APIRouter()

@router.get("/")
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # 1. Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = f"unhealthy: {e}"

    # 2. Check Redis
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        r.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["redis"] = f"unhealthy: {e}"

    # 3. Check 3rd Party API Config Status
    health_status["services"]["openai"] = "mock" if settings.is_openai_mock else "configured"
    health_status["services"]["elevenlabs"] = "mock" if settings.is_elevenlabs_mock else "configured"
    if YouTubeService.has_upload_connection():
        health_status["services"]["youtube"] = "connected"
    elif settings.is_youtube_upload_configured:
        health_status["services"]["youtube"] = "configured"
    else:
        health_status["services"]["youtube"] = "mock"
    
    return health_status
