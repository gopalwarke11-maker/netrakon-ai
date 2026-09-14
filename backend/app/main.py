"""FastAPI application entry point for NETRAKON AI."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai import model_manager
from app.api.routes import (
    ai_detect,
    ai_intrusion,
    ai_track,
    ai_risk,
    ai_behavior,
    ai_low_light,
    alert_websocket,
    alerts,
    boundaries,
    camera_processing,
    cameras,
    detections,
    health,
    intrusions,
)
from app.core.config import settings
from app.services.alert_websocket import alert_connection_manager
from app.db.session import engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Provide an explicit lifecycle hook for startup/shutdown resources."""
    # ── Startup: load YOLO model into memory ───────────────────────────────
    alert_connection_manager.bind_loop(asyncio.get_running_loop())
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL is required. Configure PostgreSQL before starting NETRAKON AI."
        )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database connection failed. Run Alembic migrations and verify DATABASE_URL.")
        raise RuntimeError("Database connection failed; NETRAKON will not use in-memory fallback.") from exc
    try:
        model_manager.load_model()
    except RuntimeError as exc:
        # Keep the rest of the API alive even if the AI model fails to load.
        # The /api/ai/detect endpoint will return 503 until the model is ready.
        logger.error("YOLO model failed to load at startup: %s", exc)
    yield
    # ── Shutdown (nothing to clean up yet) ──────────────────────────────


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend foundation for the NETRAKON AI border surveillance system.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(cameras.router, prefix=settings.api_prefix)
app.include_router(camera_processing.router, prefix=settings.api_prefix)
app.include_router(boundaries.router, prefix=settings.api_prefix)
app.include_router(alerts.router, prefix=settings.api_prefix)
app.include_router(intrusions.router, prefix=settings.api_prefix)
app.include_router(detections.router, prefix=settings.api_prefix)
app.include_router(ai_detect.router, prefix=settings.api_prefix)
app.include_router(ai_track.router, prefix=settings.api_prefix)
app.include_router(ai_intrusion.router, prefix=settings.api_prefix)
app.include_router(ai_risk.router, prefix=settings.api_prefix)
app.include_router(ai_behavior.router, prefix=settings.api_prefix)
app.include_router(ai_low_light.router, prefix=settings.api_prefix)
app.include_router(alert_websocket.router)



@app.get("/", tags=["root"], summary="Backend service information")
def root() -> dict[str, str]:
    """Return basic information about the running backend."""
    return {"service": settings.app_name, "version": settings.app_version}
