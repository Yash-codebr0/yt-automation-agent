from fastapi import APIRouter

from backend.app.api import analytics, auth, health, projects, trends, ws, youtube

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
api_router.include_router(ws.router, tags=["websocket"])
