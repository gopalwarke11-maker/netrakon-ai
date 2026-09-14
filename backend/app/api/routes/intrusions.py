"""Persistent intrusion-event history API."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status

from app.models.intrusion import IntrusionEvent
from app.services.intrusion_service import intrusion_service

router = APIRouter(prefix="/intrusions", tags=["intrusions"])


@router.get("", response_model=list[IntrusionEvent])
def list_intrusions(
    camera_id: str | None = None, boundary_id: str | None = None, severity: str | None = None,
    start_time: datetime | None = None, end_time: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
) -> list[IntrusionEvent]:
    return intrusion_service.list(camera_id, boundary_id, severity, start_time, end_time, limit, offset)


@router.get("/{event_id}", response_model=IntrusionEvent)
def get_intrusion(event_id: str) -> IntrusionEvent:
    event = intrusion_service.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intrusion event not found")
    return event
