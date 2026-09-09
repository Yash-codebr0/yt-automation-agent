import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.database import Base

class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    views = Column(Integer, default=0)
    watch_time = Column(Float, default=0.0)  # In hours
    ctr = Column(Float, default=0.0)  # Click-Through Rate in %
    subscribers_gained = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    retention_rate = Column(Float, default=0.0)  # Average retention in %
    traffic_sources = Column(String, nullable=True)  # JSON-encoded traffic sources
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project")

