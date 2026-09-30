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
    admin_control,
    alert_websocket,
    alerts,
    auth,
    boundaries,
    camera_processing,
    cameras,
    detections,
    health,
    intrusions,
    password_reset,
)
from app.core.config import settings
from app.services.alert_websocket import alert_connection_manager
from app.db.session import engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Provide an explicit lifecycle hook for startup/shutdown resources."""
    # ── Startup ─────────────────────────────────────────────────────────────
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

    _seed_demo_cameras()
    logger.info("NETRAKON AI backend initialized (lightweight startup, YOLO lazy loading enabled).")
    yield
    # ── Shutdown (nothing to clean up yet) ──────────────────────────────


def _seed_demo_cameras() -> None:
    """Ensure CAM-01 and CAM-02 demo cameras point to local demo videos."""
    from app.db.models import CameraRecord
    from app.db.session import SessionLocal

    try:
        with SessionLocal.begin() as db:
            c1 = db.get(CameraRecord, "CAM-01")
            if not c1:
                c1 = CameraRecord(id="CAM-01")
                db.add(c1)
            c1.name = "Camera 1"
            c1.sector = "SECTOR 1"
            c1.location = "North Gate"
            c1.status = "ONLINE"
            c1.source_type = "FILE"
            c1.stream_url = "camera_1.mp4"
            c1.storage_key = None

            c2 = db.get(CameraRecord, "CAM-02")
            if not c2:
                c2 = CameraRecord(id="CAM-02")
                db.add(c2)
            c2.name = "Camera 2"
            c2.sector = "SECTOR 2"
            c2.location = "East Border"
            c2.status = "ONLINE"
            c2.source_type = "FILE"
            c2.stream_url = "camera_2.mp4"
            c2.storage_key = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to seed default demo cameras: %s", exc)


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
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin_control.router, prefix=settings.api_prefix)
app.include_router(password_reset.router, prefix=settings.api_prefix)
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
