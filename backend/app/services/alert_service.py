"""Database-backed alert business logic."""

from datetime import datetime
from sqlalchemy import select

from app.db.models import AlertRecord
from app.db.session import SessionLocal
from app.models.alert import Alert, AlertCreate, AlertUpdate


def _alert(row: AlertRecord) -> Alert:
    return Alert.model_validate(row, from_attributes=True)


class AlertService:
    def list(self, camera_id: str | None = None, severity: str | None = None, status: str | None = None,
             start_time: datetime | None = None, end_time: datetime | None = None) -> list[Alert]:
        with SessionLocal() as db:
            query = select(AlertRecord).order_by(AlertRecord.timestamp.desc())
            if camera_id: query = query.where(AlertRecord.camera_id == camera_id)
            if severity: query = query.where(AlertRecord.severity == severity)
            if status: query = query.where(AlertRecord.status == status)
            if start_time: query = query.where(AlertRecord.timestamp >= start_time)
            if end_time: query = query.where(AlertRecord.timestamp <= end_time)
            return [_alert(row) for row in db.scalars(query).all()]

    def get(self, alert_id: str) -> Alert | None:
        with SessionLocal() as db:
            row = db.get(AlertRecord, alert_id)
            return _alert(row) if row else None

    def create(self, payload: AlertCreate) -> Alert:
        with SessionLocal.begin() as db:
            ids = set(db.scalars(select(AlertRecord.id)).all()); number = 1
            while f"ALT-{number:04d}" in ids: number += 1
            row = AlertRecord(id=f"ALT-{number:04d}", **payload.model_dump())
            db.add(row); db.flush(); return _alert(row)

    def update(self, alert_id: str, payload: AlertUpdate) -> Alert | None:
        with SessionLocal.begin() as db:
            row = db.get(AlertRecord, alert_id)
            if row is None: return None
            for field, value in payload.model_dump(exclude_unset=True).items(): setattr(row, field, value)
            db.flush(); return _alert(row)


alert_service = AlertService()
