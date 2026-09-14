"""Behavior observation persistence and retrieval service."""

from __future__ import annotations

import logging

from app.ai.behavior_schemas import BehaviorAssessment, BehaviorAssessmentCreate
from app.db.models import BehaviorObservationRecord
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class BehaviorService:
    """Service for persisting and retrieving behavior observations."""

    @staticmethod
    def _to_assessment(record: BehaviorObservationRecord) -> BehaviorAssessment:
        observations = [
            {
                "behavior_type": obs["behavior_type"],
                "severity": obs["severity"],
                "confidence": obs["confidence"],
                "duration_seconds": obs.get("duration_seconds"),
                "evidence": obs.get("evidence", {}),
                "reason": obs["reason"],
                "detected_at": obs["detected_at"],
            }
            for obs in (record.observations or [])
        ]
        return BehaviorAssessment(
            id=record.id,
            camera_id=record.camera_id,
            track_id=record.track_id,
            observations=observations,  # type: ignore[arg-type]
            behavior_score=record.behavior_score,
            primary_behavior=record.behavior_type,
            assessed_at=record.assessed_at,
            duration_window_seconds=record.duration_window_seconds,
            intrusion_event_id=record.intrusion_event_id,
            created_at=record.created_at,
        )
    
    def create_behavior(
        self,
        behavior: BehaviorAssessmentCreate,
    ) -> BehaviorAssessment | None:
        """Create and persist a behavior observation.
        
        Args:
            behavior: BehaviorAssessmentCreate with assessment data
            
        Returns:
            BehaviorAssessment with ID, or None if creation failed
        """
        session = SessionLocal()
        try:
            # Serialize observations to JSON for storage
            observations_dict = [
                {
                    "behavior_type": obs.behavior_type,
                    "severity": obs.severity,
                    "confidence": obs.confidence,
                    "duration_seconds": obs.duration_seconds,
                    "evidence": obs.evidence,
                    "reason": obs.reason,
                    "detected_at": obs.detected_at.isoformat(),
                }
                for obs in behavior.observations
            ]

            # Idempotency is backed by PostgreSQL so a worker restart cannot
            # replay the same camera/track behavior state into new rows.
            existing = session.query(BehaviorObservationRecord).filter(
                BehaviorObservationRecord.camera_id == behavior.camera_id,
                BehaviorObservationRecord.track_id == behavior.track_id,
                BehaviorObservationRecord.behavior_type == (behavior.primary_behavior or "UNKNOWN"),
                BehaviorObservationRecord.behavior_score == behavior.behavior_score,
            ).order_by(BehaviorObservationRecord.created_at.desc()).first()
            if existing is not None:
                session.rollback()
                return self._to_assessment(existing)
            
            record = BehaviorObservationRecord(
                id=behavior.id,
                camera_id=behavior.camera_id,
                track_id=behavior.track_id,
                intrusion_event_id=behavior.intrusion_event_id,
                behavior_type=behavior.primary_behavior or "UNKNOWN",
                behavior_score=behavior.behavior_score,
                observations=observations_dict,
                duration_window_seconds=behavior.duration_window_seconds,
                assessed_at=behavior.assessed_at,
            )
            
            session.add(record)
            session.commit()
            
            logger.info(
                "Behavior observation created: %s (track=%d, camera=%s, score=%d)",
                behavior.id,
                behavior.track_id,
                behavior.camera_id,
                behavior.behavior_score,
            )
            
            # Return the created assessment
            return self._to_assessment(record)
        
        except Exception as exc:
            logger.exception("Failed to create behavior observation: %s", exc)
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_behavior(self, behavior_id: str) -> BehaviorAssessment | None:
        """Retrieve a behavior observation by ID.
        
        Args:
            behavior_id: Behavior observation ID
            
        Returns:
            BehaviorAssessment if found, None otherwise
        """
        session = SessionLocal()
        try:
            record = session.query(BehaviorObservationRecord).filter(
                BehaviorObservationRecord.id == behavior_id
            ).first()
            
            if not record:
                return None
            
            # Reconstruct observations from JSON
            observations = [
                {
                    "behavior_type": obs["behavior_type"],
                    "severity": obs["severity"],
                    "confidence": obs["confidence"],
                    "duration_seconds": obs.get("duration_seconds"),
                    "evidence": obs.get("evidence", {}),
                    "reason": obs["reason"],
                    "detected_at": obs["detected_at"],
                }
                for obs in (record.observations or [])
            ]
            
            return BehaviorAssessment(
                id=record.id,
                camera_id=record.camera_id,
                track_id=record.track_id,
                observations=observations,  # type: ignore
                behavior_score=record.behavior_score,
                primary_behavior=record.behavior_type,
                assessed_at=record.assessed_at,
                duration_window_seconds=record.duration_window_seconds,
                intrusion_event_id=record.intrusion_event_id,
                created_at=record.created_at,
            )
        
        except Exception as exc:
            logger.exception("Failed to retrieve behavior observation: %s", exc)
            return None
        finally:
            session.close()
    
    def get_track_behaviors(self, camera_id: str, track_id: int) -> list[BehaviorAssessment]:
        """Retrieve all behavior observations for a track.
        
        Args:
            camera_id: Camera ID
            track_id: Track ID
            
        Returns:
            List of BehaviorAssessment records
        """
        session = SessionLocal()
        try:
            records = session.query(BehaviorObservationRecord).filter(
                BehaviorObservationRecord.camera_id == camera_id,
                BehaviorObservationRecord.track_id == track_id,
            ).order_by(BehaviorObservationRecord.created_at.desc()).all()
            
            behaviors = []
            for record in records:
                observations = [
                    {
                        "behavior_type": obs["behavior_type"],
                        "severity": obs["severity"],
                        "confidence": obs["confidence"],
                        "duration_seconds": obs.get("duration_seconds"),
                        "evidence": obs.get("evidence", {}),
                        "reason": obs["reason"],
                        "detected_at": obs["detected_at"],
                    }
                    for obs in (record.observations or [])
                ]
                
                behaviors.append(BehaviorAssessment(
                    id=record.id,
                    camera_id=record.camera_id,
                    track_id=record.track_id,
                    observations=observations,  # type: ignore
                    behavior_score=record.behavior_score,
                    primary_behavior=record.behavior_type,
                    assessed_at=record.assessed_at,
                    duration_window_seconds=record.duration_window_seconds,
                    intrusion_event_id=record.intrusion_event_id,
                    created_at=record.created_at,
                ))
            
            return behaviors
        
        except Exception as exc:
            logger.exception("Failed to retrieve track behaviors: %s", exc)
            return []
        finally:
            session.close()
    
    def get_camera_behaviors(
        self,
        camera_id: str,
        limit: int = 100,
    ) -> list[BehaviorAssessment]:
        """Retrieve recent behavior observations for a camera.
        
        Args:
            camera_id: Camera ID
            limit: Maximum number of records to return
            
        Returns:
            List of BehaviorAssessment records
        """
        session = SessionLocal()
        try:
            records = session.query(BehaviorObservationRecord).filter(
                BehaviorObservationRecord.camera_id == camera_id,
            ).order_by(BehaviorObservationRecord.created_at.desc()).limit(limit).all()
            
            behaviors = []
            for record in records:
                observations = [
                    {
                        "behavior_type": obs["behavior_type"],
                        "severity": obs["severity"],
                        "confidence": obs["confidence"],
                        "duration_seconds": obs.get("duration_seconds"),
                        "evidence": obs.get("evidence", {}),
                        "reason": obs["reason"],
                        "detected_at": obs["detected_at"],
                    }
                    for obs in (record.observations or [])
                ]
                
                behaviors.append(BehaviorAssessment(
                    id=record.id,
                    camera_id=record.camera_id,
                    track_id=record.track_id,
                    observations=observations,  # type: ignore
                    behavior_score=record.behavior_score,
                    primary_behavior=record.behavior_type,
                    assessed_at=record.assessed_at,
                    duration_window_seconds=record.duration_window_seconds,
                    intrusion_event_id=record.intrusion_event_id,
                    created_at=record.created_at,
                ))
            
            return behaviors
        
        except Exception as exc:
            logger.exception("Failed to retrieve camera behaviors: %s", exc)
            return []
        finally:
            session.close()


# Global behavior service instance
behavior_service = BehaviorService()
