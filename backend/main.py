import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging_config import setup_logging
from backend.app.api.api import api_router

# Bootstrap structured JSON logging before anything else
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description=(
        "AI YouTube Empire – Autonomous Multi-Agent Video Production System. "
        "Powered by LangGraph, GPT-4o, ElevenLabs, and the YouTube API."
    ),
    version="2.0.0",
)

# ── Prometheus metrics ────────────────────────────────────────────────────────
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    logger.info("Prometheus FastAPI Instrumentator mounted at /metrics")
except ImportError:
    logger.warning("prometheus_fastapi_instrumentator not installed – metrics endpoint disabled.")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes (REST + WebSocket) ─────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)

# ── Static media files (thumbnails, voiceovers, rendered videos) ──────────────
if os.path.exists(settings.MEDIA_DIR):
    app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")


@app.on_event("startup")
def on_startup():
    logger.info("Starting AI YouTube Empire API v2.0.0...")
    init_db()
    logger.info("Database tables verified / initialized.")


@app.get("/")
def read_root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": "2.0.0",
        "docs": f"{settings.API_V1_STR}/openapi.json",
    }
