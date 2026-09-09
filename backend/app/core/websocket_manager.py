import asyncio
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections scoped to individual project IDs."""

    def __init__(self):
        # Map: project_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection for a project."""
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        self.active_connections[project_id].add(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket):
        """Remove a disconnected WebSocket from the registry."""
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            # Clean up the set if it's now empty
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast_to_project(self, project_id: str, data: dict):
        """Send a JSON message to all active connections for a project."""
        if project_id not in self.active_connections:
            return
        dead = set()
        for ws in self.active_connections[project_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections[project_id].discard(ws)

    async def send_personal(self, websocket: WebSocket, data: dict):
        """Send a JSON message to a single WebSocket connection."""
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    def connection_count(self, project_id: str) -> int:
        """Return the number of active connections for a project."""
        return len(self.active_connections.get(project_id, set()))


# Module-level singleton shared across the entire application
manager = ConnectionManager()
