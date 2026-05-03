import asyncio
import json
import logging
from collections import defaultdict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Redis pub/sub channel prefix: "progress:{tenant_id}"
_PROGRESS_CHANNEL_PREFIX = "progress"


class WebSocketManager:
    """
    Manages WebSocket connections per tenant.

    Architecture:
    - Celery workers publish progress events to Redis: ``progress:{tenant_id}``
    - The FastAPI server runs ``subscribe_and_forward()`` as a background task,
      listens on ``progress:*`` via Redis pattern-subscribe, and pushes payloads
      to the matching tenant's WebSocket clients.
    - This decouples the worker process from the API server process.
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
        """Push a progress event to all WebSocket clients for this tenant."""
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

    # ------------------------------------------------------------------
    # Redis Pub/Sub subscriber (runs as asyncio background task in FastAPI)
    # ------------------------------------------------------------------

    async def subscribe_and_forward(self, redis_url: str):
        """
        Long-running coroutine.  Subscribe to ``progress:*`` on Redis and
        forward every message to the matching tenant's WebSocket clients.

        Start this once inside the FastAPI lifespan:
            asyncio.create_task(ws_manager.subscribe_and_forward(redis_url))
        """
        import redis.asyncio as aioredis

        while True:
            try:
                client = aioredis.Redis.from_url(redis_url, decode_responses=False)
                pubsub = client.pubsub()
                pattern = f"{_PROGRESS_CHANNEL_PREFIX}:*"
                await pubsub.psubscribe(pattern)
                logger.info("WebSocket bridge: subscribed to Redis pattern '%s'", pattern)

                async for message in pubsub.listen():
                    if message.get("type") != "pmessage":
                        continue
                    try:
                        raw_channel: bytes = message["channel"]
                        channel = raw_channel.decode() if isinstance(raw_channel, bytes) else raw_channel
                        # channel = "progress:{tenant_id}"
                        tenant_id = int(channel.split(":", 1)[1])

                        raw_data = message.get("data", b"")
                        payload_str = raw_data.decode() if isinstance(raw_data, bytes) else raw_data
                        data = json.loads(payload_str)

                        await self.send_progress(
                            tenant_id=tenant_id,
                            entity_type=data.get("entity_type", ""),
                            entity_id=data.get("entity_id", 0),
                            progress=data.get("progress", 0),
                            stage=data.get("stage", ""),
                            message=data.get("message", ""),
                        )
                    except Exception as exc:
                        logger.warning("WS bridge: failed to forward message: %s", exc)

                await pubsub.punsubscribe(pattern)
                await client.aclose()

            except asyncio.CancelledError:
                logger.info("WebSocket bridge: subscriber task cancelled")
                return
            except Exception as exc:
                logger.warning("WebSocket bridge: Redis connection lost (%s) — retrying in 5s", exc)
                await asyncio.sleep(5)


ws_manager = WebSocketManager()


# ---------------------------------------------------------------------------
# Module-level helper used by Celery tasks (runs inside asyncio.run())
# ---------------------------------------------------------------------------

async def publish_progress(
    redis_url: str,
    tenant_id: int,
    entity_type: str,
    entity_id: int,
    progress: int,
    stage: str,
    message: str = "",
) -> None:
    """
    Publish a progress event to Redis so the FastAPI server can forward it
    to WebSocket clients.  Call this from async Celery task helpers.
    """
    import redis.asyncio as aioredis

    payload = json.dumps({
        "entity_type": entity_type,
        "entity_id": entity_id,
        "progress": progress,
        "stage": stage,
        "message": message,
    })
    channel = f"{_PROGRESS_CHANNEL_PREFIX}:{tenant_id}"
    client = aioredis.Redis.from_url(redis_url, decode_responses=False)
    try:
        await client.publish(channel, payload)
    finally:
        await client.aclose()
