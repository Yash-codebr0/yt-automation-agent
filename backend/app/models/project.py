import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.database import Base
from backend.app.models.user import User  # noqa: F401
from backend.app.models.trend import Trend  # noqa: F401
from backend.app.models.youtube_account import YouTubeAccount  # noqa: F401


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    trend_id = Column(String, ForeignKey("trends.id"), nullable=True)
    youtube_account_id = Column(String, ForeignKey("youtube_accounts.id"), nullable=True)
    title = Column(String, nullable=False)
    niche = Column(String, nullable=False)  # Free-form: "Gaming", "AI", "Cooking", etc.
    status = Column(String, default="draft")  # "draft", "running", "completed", "failed", etc.
    is_custom = Column(Boolean, default=False)  # Flag for custom campaign
    custom_title = Column(String, nullable=True)  # Optional custom video title
    
    # Script parts
    script_title = Column(String, nullable=True)
    script_hook = Column(String, nullable=True)
    script_body = Column(Text, nullable=True)
    script_cta = Column(String, nullable=True)
    
    # Assets URLs/Paths
    voiceover_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    shorts_video_url = Column(String, nullable=True)
    
    # SEO
    seo_title = Column(String, nullable=True)
    seo_description = Column(Text, nullable=True)
    seo_tags = Column(String, nullable=True)  # Comma separated
    
    # YouTube Upload Info
    scheduled_publish_time = Column(DateTime, nullable=True)
    youtube_video_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    trend = relationship("Trend")
    youtube_account = relationship("YouTubeAccount", back_populates="projects")
