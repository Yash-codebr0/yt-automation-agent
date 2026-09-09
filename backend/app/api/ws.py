from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.websocket_manager import manager
from backend.app.core.security import decode_access_token
from backend.app.models.log import AgentLog

router = APIRouter()


@router.websocket("/projects/{project_id}/stream")
async def websocket_endpoint(
    project_id: str,
    websocket: WebSocket,
    token: str = "",
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint that streams real-time agent log events to the client
    for a specific project. Requires a valid JWT passed as ?token=<jwt>.
    """
    # Authenticate via query-param token
    user_id = decode_access_token(token) if token else None
    if not user_id:
        await websocket.close(code=1008)  # 1008 = Policy Violation / unauthorized
        return

    await manager.connect(project_id, websocket)

    try:
        # Immediately replay recent logs on connection so the UI is populated
        recent_logs = (
            db.query(AgentLog)
            .filter(AgentLog.project_id == project_id)
            .order_by(AgentLog.created_at.desc())
            .limit(50)
            .all()
        )
        for log in reversed(recent_logs):
            await websocket.send_json({
                "type": "log",
                "agent": log.agent_name,
                "status": log.status,
                "message": log.log_message,
                "timestamp": log.created_at.isoformat() if log.created_at else "",
            })

        # Notify client it is live
        await websocket.send_json({"type": "connected", "projectId": project_id})

        # Keep connection alive; new logs are pushed via
        # manager.broadcast_to_project() from the workflow tasks
        while True:
            # Receive any keep-alive pings from the client; we don't act on them
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
    except Exception:
        manager.disconnect(project_id, websocket)
