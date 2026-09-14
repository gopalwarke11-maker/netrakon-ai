"""Alert API routes."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.alert import Alert, AlertCreate, AlertUpdate
from app.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert], summary="List alerts")
def list_alerts(camera_id: str | None = None, severity: str | None = None, status_filter: str | None = None,
                start_time: datetime | None = None, end_time: datetime | None = None) -> list[Alert]:
    return alert_service.list(camera_id, severity, status_filter, start_time, end_time)


@router.get("/{alert_id}", response_model=Alert, summary="Get an alert")
def get_alert(alert_id: str) -> Alert:
    alert = alert_service.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.post("", response_model=Alert, status_code=status.HTTP_201_CREATED, summary="Create an alert")
def create_alert(payload: AlertCreate) -> Alert:
    try:
        return alert_service.create(payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert conflicts with existing data.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc


@router.patch("/{alert_id}", response_model=Alert, summary="Update an alert")
def update_alert(alert_id: str, payload: AlertUpdate) -> Alert:
    alert = alert_service.update(alert_id, payload)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert
