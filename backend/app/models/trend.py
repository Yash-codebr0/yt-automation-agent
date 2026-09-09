import uuid
from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime
from backend.app.core.database import Base

class Trend(Base):
    __tablename__ = "trends"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True, nullable=False)
    query = Column(String, nullable=False)
    source = Column(String, default="Google Trends")  # "Google Trends", "YouTube API"
    score = Column(Float, default=0.0)  # Calculated score/popularity
    category = Column(String, default="General")
    analyzed_at = Column(DateTime, default=datetime.utcnow)
