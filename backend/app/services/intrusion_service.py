"""Transactional persistence and history queries for confirmed intrusions."""

from datetime import datetime

from sqlalchemy import select

from app.ai.risk_engine import calculate_risk
from app.db.models import AlertRecord, IntrusionEventRecord
from app.db.session import SessionLocal
from app.models.alert import Alert, AlertCreate
from app.models.intrusion import IntrusionEvent, IntrusionPoint


def _event(row: IntrusionEventRecord) -> IntrusionEvent:
    return IntrusionEvent(
        id=row.id, camera_id=row.camera_id or "DELETED-CAMERA", boundary_id=row.boundary_id or "DELETED-BOUNDARY",
        boundary_name=row.boundary_name, track_id=row.track_id, object_class=row.object_class,
        confidence=row.confidence, timestamp=row.timestamp,
        previous_anchor=IntrusionPoint.model_validate(row.previous_anchor), current_anchor=IntrusionPoint.model_validate(row.current_anchor),
        crossing_direction=row.crossing_direction, severity=row.severity, alert_id=row.alert_id,
        event_type=row.event_type, status=row.status,
    )


def _alert(row: AlertRecord) -> Alert:
    return Alert.model_validate(row, from_attributes=True)


def _next_id(db, model, prefix: str) -> str:
    ids = set(db.scalars(select(model.id)).all())
    number = 1
    width = 4
    while f"{prefix}-{number:0{width}d}" in ids:
        number += 1
    return f"{prefix}-{number:0{width}d}"


class IntrusionService:
    def create_with_alert(self, event: IntrusionEvent, alert_payload: AlertCreate) -> tuple[IntrusionEvent, Alert]:
        """Atomically persist an event and its alert before WebSocket delivery.
        
        Also calculates and persists risk assessment.
        """
        with SessionLocal.begin() as db:
            # Count prior intrusions for this camera/boundary/track (for repeat_count)
            prior_count = db.scalars(
                select(IntrusionEventRecord).where(
                    IntrusionEventRecord.camera_id == event.camera_id,
                    IntrusionEventRecord.boundary_id == event.boundary_id,
                    IntrusionEventRecord.track_id == event.track_id,
                    IntrusionEventRecord.status == "ACTIVE",
                )
            ).all()
            repeat_count = len(prior_count) + 1  # +1 for this new event
            
            # Calculate risk assessment
            risk_assessment = calculate_risk(event, repeat_count=repeat_count - 1)
            
            # Persist event and alert
            event_id = _next_id(db, IntrusionEventRecord, "EVT")
            alert_id = _next_id(db, AlertRecord, "ALT")
            
            alert = AlertRecord(
                id=alert_id,
                event_id=event_id,
                risk_score=risk_assessment.risk_score,
                risk_level=risk_assessment.risk_level,
                **alert_payload.model_dump(exclude={"event_id"})
            )
            db.add(alert)
            
            # Serialize risk factors for storage
            risk_factors = [
                {
                    "factor": f.factor,
                    "value": f.value,
                    "contribution": f.contribution,
                    "reason": f.reason,
                }
                for f in risk_assessment.factors
            ]
            
            row = IntrusionEventRecord(
                id=event_id,
                camera_id=event.camera_id,
                boundary_id=event.boundary_id,
                boundary_name=event.boundary_name,
                track_id=event.track_id,
                object_class=event.object_class,
                confidence=event.confidence,
                timestamp=event.timestamp,
                previous_anchor=event.previous_anchor.model_dump(),
                current_anchor=event.current_anchor.model_dump(),
                crossing_direction=event.crossing_direction,
                severity=event.severity,
                status=event.status,
                event_type=event.event_type,
                alert_id=alert_id,
                risk_score=risk_assessment.risk_score,
                risk_level=risk_assessment.risk_level,
                risk_factors=risk_factors,
            )
            db.add(row)
            db.flush()
            return _event(row), _alert(alert)

    def list(self, camera_id: str | None = None, boundary_id: str | None = None, severity: str | None = None,
             start_time: datetime | None = None, end_time: datetime | None = None, limit: int = 100, offset: int = 0) -> list[IntrusionEvent]:
        with SessionLocal() as db:
            query = select(IntrusionEventRecord).order_by(IntrusionEventRecord.timestamp.desc())
            if camera_id: query = query.where(IntrusionEventRecord.camera_id == camera_id)
            if boundary_id: query = query.where(IntrusionEventRecord.boundary_id == boundary_id)
            if severity: query = query.where(IntrusionEventRecord.severity == severity)
            if start_time: query = query.where(IntrusionEventRecord.timestamp >= start_time)
            if end_time: query = query.where(IntrusionEventRecord.timestamp <= end_time)
            return [_event(row) for row in db.scalars(query.limit(limit).offset(offset)).all()]

    def get(self, event_id: str) -> IntrusionEvent | None:
        with SessionLocal() as db:
            row = db.get(IntrusionEventRecord, event_id)
            return _event(row) if row else None


intrusion_service = IntrusionService()
