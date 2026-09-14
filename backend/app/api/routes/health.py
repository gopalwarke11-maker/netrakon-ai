"""Health and service status endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import settings
from app.ai import model_manager
from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health", summary="Check backend health")
def health_check() -> dict[str, str]:
    """Return a lightweight status response for service monitoring."""
    return {
        "status": "ok",
        "service": f"{settings.app_name} Backend",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/ready", summary="Check backend readiness")
def readiness_check() -> dict[str, object]:
    """Report whether critical database and model dependencies are ready."""
    database_ready = False
    if engine is not None:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            database_ready = True
        except Exception:  # noqa: BLE001
            database_ready = False

    model_ready = model_manager.is_model_loaded()
    payload = {
        "status": "ready" if database_ready and model_ready else "not_ready",
        "database": database_ready,
        "model": model_ready,
    }
    if not database_ready or not model_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return payload