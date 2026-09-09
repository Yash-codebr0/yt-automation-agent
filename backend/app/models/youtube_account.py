import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.database import Base


class YouTubeAccount(Base):
    """Stores OAuth credentials for a connected YouTube channel.

    One user can have many accounts. Exactly one per user is flagged
    `is_active=True` — that account is used for uploads unless a project
    overrides it with a specific `youtube_account_id`.
    """
    __tablename__ = "youtube_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Human label the user sets, e.g. "Gaming Channel"
    nickname = Column(String, nullable=False, default="My Channel")

    # Populated after OAuth by querying the channels.list API
    channel_id = Column(String, nullable=True)   # e.g. "UCxxxxx"
    channel_title = Column(String, nullable=True)  # e.g. "TechWithJohn"
    channel_thumbnail = Column(String, nullable=True)  # profile picture URL

    # Per-account token file — "media/yt_tokens/acc_{id}.json"
    token_file = Column(String, nullable=False)

    # Only one account per user is active at a time
    is_active = Column(Boolean, default=False, nullable=False)

    connected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    projects = relationship("Project", back_populates="youtube_account")
