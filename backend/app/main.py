import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.core.ws_manager import ws_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MinIO bucket on startup
    try:
        from app.core.storage import get_minio_client
        get_minio_client()
    except Exception:
        pass

    # Start Redis → WebSocket bridge (forwards Celery progress events to clients)
    subscriber_task = asyncio.create_task(
        ws_manager.subscribe_and_forward(settings.redis_url),
        name="ws_redis_bridge",
    )

    yield

    # Graceful shutdown
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OTD AI 述标教练",
    version="0.1.0",
    description="AI Pitch Coach for B2B sales teams",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feature gate: must be added AFTER CORS (middleware stack is LIFO)
from app.middleware.feature_gate_middleware import FeatureGateMiddleware  # noqa: E402
app.add_middleware(FeatureGateMiddleware)

# Register API routers
from app.api.v1 import auth, pitch_tasks, pitch_plans, rehearsals, narrations, reviews, knowledge, training, daily_practice, conversion, subscription, team, rubrics, evaluators, billing, dashboard, post_mortem, scenarios, open_api, gamification, golden_scripts, notifications, team_practice  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(pitch_tasks.router, prefix="/api/v1")
app.include_router(pitch_plans.router, prefix="/api/v1")
app.include_router(rehearsals.router, prefix="/api/v1")
app.include_router(narrations.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(daily_practice.router, prefix="/api/v1")
app.include_router(conversion.router, prefix="/api/v1")
app.include_router(subscription.router, prefix="/api/v1")
app.include_router(team.router, prefix="/api/v1")
app.include_router(rubrics.router, prefix="/api/v1")
app.include_router(evaluators.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(post_mortem.router, prefix="/api/v1")
app.include_router(scenarios.router, prefix="/api/v1")
app.include_router(open_api.router, prefix="/api/v1")
app.include_router(gamification.router, prefix="/api/v1")
app.include_router(golden_scripts.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(team_practice.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: int):
    """Real-time progress push for async tasks (plan generation, scoring, etc.)"""
    await ws_manager.connect(websocket, tenant_id)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, tenant_id)
