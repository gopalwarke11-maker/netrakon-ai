"""Risk assessment service for intrusion events."""

from __future__ import annotations

from sqlalchemy import select

from app.ai.risk_engine import calculate_risk as calculate_risk_score
from app.ai.risk_schemas import RiskAssessment as RiskAssessmentSchema
from app.db.models import IntrusionEventRecord
from app.db.session import SessionLocal
from app.models.intrusion import IntrusionEvent, IntrusionPoint


class RiskService:
    """Calculate, persist, and query risk assessments."""
    
    def calculate_risk(
        self,
        event: IntrusionEvent,
        repeat_count: int = 1,
    ) -> RiskAssessmentSchema:
        """Calculate risk for an intrusion event.
        
        Args:
            event: The intrusion event to assess
            repeat_count: Number of times this track/camera/boundary has intruded
            
        Returns:
            RiskAssessmentSchema with deterministic score, level, and factors
        """
        assessment = calculate_risk_score(event, repeat_count)
        
        return RiskAssessmentSchema(
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            factors=[
                {
                    "factor": f.factor,
                    "value": f.value,
                    "contribution": f.contribution,
                    "reason": f.reason,
                }
                for f in assessment.factors
            ],
            assessed_at=assessment.assessed_at,
            intrusion_event_id=assessment.intrusion_event_id,
            camera_id=assessment.camera_id,
            boundary_id=assessment.boundary_id,
            track_id=assessment.track_id,
        )
    
    def get_repeat_count(
        self,
        camera_id: str,
        boundary_id: str,
        track_id: int,
    ) -> int:
        """Count number of confirmed intrusions for the same camera/boundary/track.
        
        Args:
            camera_id: Camera ID
            boundary_id: Boundary ID
            track_id: Track ID
            
        Returns:
            Count of confirmed intrusion events (>= 1)
        """
        with SessionLocal() as db:
            count = db.scalars(
                select(IntrusionEventRecord).where(
                    IntrusionEventRecord.camera_id == camera_id,
                    IntrusionEventRecord.boundary_id == boundary_id,
                    IntrusionEventRecord.track_id == track_id,
                    IntrusionEventRecord.status == "ACTIVE",
                )
            ).all()
            return len(count)
    
    def get_risk(self, event_id: str) -> RiskAssessmentSchema | None:
        """Retrieve stored risk assessment for an intrusion event.
        
        Args:
            event_id: Intrusion event ID
            
        Returns:
            RiskAssessmentSchema if exists, None otherwise
        """
        with SessionLocal() as db:
            row = db.get(IntrusionEventRecord, event_id)
            if not row or not row.risk_score:
                return None
            
            return RiskAssessmentSchema(
                risk_score=row.risk_score,
                risk_level=row.risk_level or "UNKNOWN",
                factors=row.risk_factors or [],
                assessed_at=row.created_at,
                intrusion_event_id=row.id,
                camera_id=row.camera_id,
                boundary_id=row.boundary_id,
                track_id=row.track_id,
            )


risk_service = RiskService()
