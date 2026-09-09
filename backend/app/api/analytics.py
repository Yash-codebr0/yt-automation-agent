from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from backend.app.core.database import get_db
from backend.app.models.project import Project
from backend.app.models.analytics import Analytics
from backend.app.schemas.analytics import DashboardStats, AnalyticsOut
from backend.app.api.deps import get_current_user
from backend.app.models.user import User

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregate total metrics from all user projects."""
    project_ids = db.query(Project.id).filter(Project.user_id == current_user.id).all()
    project_ids = [p[0] for p in project_ids]
    
    if not project_ids:
        return {
            "total_views": 0,
            "total_watch_time": 0.0,
            "avg_ctr": 0.0,
            "total_subscribers": 0,
            "total_projects": 0
        }
        
    stats = db.query(
        func.sum(Analytics.views),
        func.sum(Analytics.watch_time),
        func.avg(Analytics.ctr),
        func.sum(Analytics.subscribers_gained),
        func.sum(Analytics.revenue)
    ).filter(Analytics.project_id.in_(project_ids)).first()
    
    return {
        "total_views": stats[0] or 0,
        "total_watch_time": stats[1] or 0.0,
        "avg_ctr": float(stats[2] or 0.0),
        "total_subscribers": stats[3] or 0,
        "total_projects": len(project_ids),
        "total_revenue": float(stats[4] or 0.0)
    }

@router.get("/charts", response_model=List[Dict[str, Any]])
def get_chart_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve day-by-day metrics aggregation for analytics graphs."""
    project_ids = db.query(Project.id).filter(Project.user_id == current_user.id).all()
    project_ids = [p[0] for p in project_ids]
    
    if not project_ids:
        return []
        
    # Query analytics entries sorted by date
    records = db.query(Analytics).filter(Analytics.project_id.in_(project_ids)).order_by(Analytics.recorded_at.asc()).all()
    
    chart_data = []
    # Accumulate by date
    date_map = {}
    for r in records:
        date_str = r.recorded_at.strftime("%Y-%m-%d")
        if date_str not in date_map:
            date_map[date_str] = {
                "date": date_str,
                "views": 0,
                "watch_time": 0.0,
                "subscribers": 0,
                "ctr_sum": 0.0,
                "ctr_count": 0,
                "revenue": 0.0,
                "retention_sum": 0.0,
                "retention_count": 0
            }
        date_map[date_str]["views"] += r.views
        date_map[date_str]["watch_time"] += r.watch_time
        date_map[date_str]["subscribers"] += r.subscribers_gained
        date_map[date_str]["ctr_sum"] += r.ctr
        date_map[date_str]["ctr_count"] += 1
        date_map[date_str]["revenue"] += r.revenue
        date_map[date_str]["retention_sum"] += r.retention_rate
        date_map[date_str]["retention_count"] += 1
        
    for d in sorted(date_map.keys()):
        item = date_map[d]
        avg_ctr = item["ctr_sum"] / item["ctr_count"] if item["ctr_count"] > 0 else 0.0
        avg_retention = item["retention_sum"] / item["retention_count"] if item["retention_count"] > 0 else 0.0
        chart_data.append({
            "date": item["date"],
            "views": item["views"],
            "watchTime": round(item["watch_time"], 2),
            "subscribers": item["subscribers"],
            "ctr": round(avg_ctr, 2),
            "revenue": round(item["revenue"], 2),
            "retention": round(avg_retention, 2)
        })
        
    return chart_data

