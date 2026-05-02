import asyncio
import json
from collections import defaultdict
from fastapi import WebSocket


class WebSocketManager:
    """
    Manages WebSocket connections per tenant.
    Allows broadcasting progress events to connected clients.
    """

    def __init__(self):
        # {tenant_id: [WebSocket, ...]}
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, tenant_id: int):
        await websocket.accept()
        self._connections[tenant_id].append(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: int):
        try:
            self._connections[tenant_id].remove(websocket)
        except ValueError:
            pass

    async def send_progress(
        self,
        tenant_id: int,
        entity_type: str,
        entity_id: int,
        progress: int,
        stage: str,
        message: str = "",
    ):
        payload = json.dumps({
            "type": "task_progress",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "progress": progress,
            "stage": stage,
            "message": message,
        })
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(tenant_id, [])):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, tenant_id)

    async def broadcast(self, tenant_id: int, data: dict):
        await self.send_progress(
            tenant_id=tenant_id,
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", 0),
            progress=data.get("progress", 0),
            stage=data.get("stage", ""),
            message=data.get("message", ""),
        )


ws_manager = WebSocketManager()
