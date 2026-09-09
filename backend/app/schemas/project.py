from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from backend.app.schemas.trend import TrendOut

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    niche: str = Field(..., min_length=1, max_length=80)

class ProjectCreate(ProjectBase):
    trend_id: Optional[str] = None
    youtube_account_id: Optional[str] = None
    is_custom: bool = False
    custom_title: Optional[str] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    niche: Optional[str] = Field(None, min_length=1, max_length=80)
    status: Optional[str] = None
    youtube_account_id: Optional[str] = None
    script_title: Optional[str] = None
    script_hook: Optional[str] = None
    script_body: Optional[str] = None
    script_cta: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None
    is_custom: Optional[bool] = None
    custom_title: Optional[str] = None
    video_url: Optional[str] = None
    shorts_video_url: Optional[str] = None

class ProjectOut(ProjectBase):
    id: str
    user_id: str
    trend_id: Optional[str] = None
    youtube_account_id: Optional[str] = None
    status: str
    script_title: Optional[str] = None
    script_hook: Optional[str] = None
    script_body: Optional[str] = None
    script_cta: Optional[str] = None
    voiceover_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    shorts_video_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_tags: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None
    youtube_video_id: Optional[str] = None
    is_custom: bool = False
    custom_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    trend: Optional[TrendOut] = None

    class Config:
        from_attributes = True

class AgentLogOut(BaseModel):
    id: str
    project_id: Optional[str] = None
    agent_name: str
    status: str
    log_message: str
    created_at: datetime

    class Config:
        from_attributes = True
