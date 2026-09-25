"""WebSocket connection manager for real-time run progress updates."""

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections grouped by execution run ID."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        """Accept WebSocket connection and register for run updates."""
        await websocket.accept()
        self.active_connections.setdefault(run_id, []).append(websocket)

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        """Unregister closed WebSocket connection."""
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, message: dict[str, Any]) -> None:
        """Send JSON message to all subscribers of a run."""
        if run_id not in self.active_connections:
            return

        for connection in list(self.active_connections[run_id]):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(run_id, connection)


ws_manager = ConnectionManager()
