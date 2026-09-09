import uuid
from sqlalchemy import Column, String, DateTime
from datetime import datetime
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="creator")  # "admin", "creator", "viewer"
    created_at = Column(DateTime, default=datetime.utcnow)
