from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.core.database import get_db
from backend.app.models.trend import Trend
from backend.app.schemas.trend import TrendOut
from backend.app.api.deps import get_current_user
from backend.app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[TrendOut])
def read_trends(
    niche: Optional[str] = Query(None, description="Filter trends by niche/category (case-insensitive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all trends sorted by score. Optionally filter by niche."""
    query = db.query(Trend).order_by(Trend.score.desc())
    if niche:
        # Case-insensitive partial match on category
        query = query.filter(Trend.category.ilike(f"%{niche}%"))
    return query.all()

@router.post("/hunt", status_code=status.HTTP_202_ACCEPTED)
def trigger_trend_hunt(
    niche: Optional[str] = Query(None, description="Niche to target trend hunting for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Kick off background Celery job to hunt trends, optionally for a specific niche."""
    from backend.app.tasks.workflow_tasks import hunt_trends_task

    use_celery = False
    try:
        from backend.app.core.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=1.0)
        workers = inspector.ping() if inspector else None
        if workers:
            use_celery = True
    except Exception as inspect_err:
        print(f"Celery worker check warning: {inspect_err}")

    if use_celery:
        task = hunt_trends_task.delay(niche=niche)
        return {"task_id": task.id, "status": "queued", "mode": "celery", "niche": niche}

    import threading
    thread = threading.Thread(target=hunt_trends_task, kwargs={"niche": niche})
    thread.daemon = True
    thread.start()
    return {"task_id": "thread-execution", "status": "running", "mode": "thread", "niche": niche}
