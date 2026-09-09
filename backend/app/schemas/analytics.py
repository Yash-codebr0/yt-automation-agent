from pydantic import BaseModel
from datetime import datetime

class AnalyticsOut(BaseModel):
    id: str
    project_id: str
    views: int
    watch_time: float
    ctr: float
    subscribers_gained: int
    revenue: float
    retention_rate: float
    traffic_sources: str | None = None
    recorded_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_views: int
    total_watch_time: float
    avg_ctr: float
    total_subscribers: int
    total_projects: int
    total_revenue: float

