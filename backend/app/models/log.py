import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.database import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    agent_name = Column(String, nullable=False)  # "Trend Hunter", "Script Writer", etc.
    status = Column(String, default="info")  # "info", "running", "success", "error"
    log_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project")
