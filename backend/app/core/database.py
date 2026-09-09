from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

# Adjust sqlite connection parameters if needed
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from contextlib import contextmanager

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def transactional_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    # Import models here to register them
    import backend.app.models.user
    import backend.app.models.trend
    import backend.app.models.project
    import backend.app.models.analytics
    import backend.app.models.log
    import backend.app.models.youtube_account
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate: add new columns to existing SQLite tables if missing
    if settings.DATABASE_URL.startswith("sqlite"):
        _migrate_sqlite()


def _migrate_sqlite():
    """Add missing columns to existing SQLite tables (safe to run repeatedly)."""
    migrations = [
        "ALTER TABLE projects ADD COLUMN is_custom BOOLEAN DEFAULT 0",
        "ALTER TABLE projects ADD COLUMN custom_title VARCHAR",
        "ALTER TABLE projects ADD COLUMN shorts_video_url VARCHAR",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                # Column already exists – ignore
                conn.rollback()
