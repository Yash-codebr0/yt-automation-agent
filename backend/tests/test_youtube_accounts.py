import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.models.youtube_account import YouTubeAccount
from backend.app.core.database import SessionLocal

client = TestClient(app)

def test_youtube_status_endpoint():
    response = client.get("/api/v1/youtube/status")
    assert response.status_code in [200, 401]

def test_youtube_account_creation_in_db():
    db = SessionLocal()
    try:
        from backend.app.models.user import User
        user = db.query(User).first()
        if user:
            acc = YouTubeAccount(
                user_id=user.id,
                nickname="Test Channel",
                token_file="media/yt_tokens/test_acc.json",
                is_active=False
            )
            db.add(acc)
            db.commit()
            db.refresh(acc)
            
            assert acc.id is not None
            assert acc.nickname == "Test Channel"
            
            # Clean up
            db.delete(acc)
            db.commit()
    finally:
        db.close()
