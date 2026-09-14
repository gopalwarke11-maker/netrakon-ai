"""Behavior observation schemas and Pydantic models for behavior analysis.

Provides structured definitions for:
- Behavior types and severity classifications
- Individual behavior observations with evidence
- Behavior scores and composite assessments
- API request/response schemas
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

# Behavior type definitions
BehaviorType = Literal[
    "LOITERING",
    "STATIONARY",
    "RAPID_MOVEMENT",
    "DIRECTION_REVERSAL",
    "REPEATED_APPROACH",
    "REPEATED_INTRUSION",
    "ABNORMAL_MOVEMENT",
]

BehaviorSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Behavior score contributions (summed, clamped to 0-100)
BEHAVIOR_CONTRIBUTIONS = {
    "LOITERING": 20,
    "STATIONARY": 5,
    "RAPID_MOVEMENT": 15,
    "DIRECTION_REVERSAL": 15,
    "REPEATED_APPROACH": 20,
    "REPEATED_INTRUSION": 30,
    "ABNORMAL_MOVEMENT": 25,
}

# Risk score contributions from behaviors (secondary to Phase 8 risk engine)
BEHAVIOR_RISK_CONTRIBUTIONS = {
    "LOITERING": 5,
    "STATIONARY": 0,
    "RAPID_MOVEMENT": 5,
    "DIRECTION_REVERSAL": 5,
    "REPEATED_APPROACH": 5,
    "REPEATED_INTRUSION": 10,
    "ABNORMAL_MOVEMENT": 10,
}


@dataclass
class BehaviorEvidence:
    """Supporting data for a behavior observation."""

    metric_name: str
    """Name of the measured metric (e.g., 'displacement_pixels', 'duration_seconds')"""

    metric_value: float
    """The actual measured value"""

    threshold: float
    """The threshold used for classification"""

    unit: str
    """Unit of measurement (e.g., 'pixels', 'seconds', 'degrees')"""


class BehaviorObservationSchema(BaseModel):
    """Single behavior observation for a tracked object."""

    behavior_type: BehaviorType = Field(description="Type of behavior detected")
    severity: BehaviorSeverity = Field(description="Severity classification")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in detection (0-1)")
    duration_seconds: float | None = Field(default=None, description="Duration of behavior in seconds")
    evidence: dict[str, float] = Field(default_factory=dict, description="Supporting evidence metrics")
    reason: str = Field(description="Human-readable explanation of why this behavior was detected")
    detected_at: datetime = Field(description="Timestamp when behavior was detected")


class BehaviorAssessmentBase(BaseModel):
    """Base behavior assessment without ID."""

    camera_id: str = Field(description="Camera where behavior was observed")
    track_id: int = Field(description="Track ID of the observed object")
    observations: list[BehaviorObservationSchema] = Field(
        description="List of detected behaviors"
    )
    behavior_score: int = Field(ge=0, le=100, description="Composite behavior score (0-100)")
    primary_behavior: BehaviorType | None = Field(
        default=None, description="Most significant behavior, if any"
    )
    assessed_at: datetime = Field(description="Timestamp of assessment")
    duration_window_seconds: float = Field(
        description="Duration of track history analyzed"
    )


class BehaviorAssessmentCreate(BehaviorAssessmentBase):
    """Behavior assessment data for creation."""

    intrusion_event_id: str | None = Field(
        default=None, description="Related intrusion event ID if applicable"
    )


class BehaviorAssessment(BehaviorAssessmentBase):
    """Complete behavior assessment with database fields."""

    id: str = Field(description="Unique behavior observation ID")
    intrusion_event_id: str | None = Field(
        default=None, description="Related intrusion event ID if applicable"
    )
    created_at: datetime = Field(description="When assessment was recorded")


class BehaviorTestRequest(BaseModel):
    """Synthetic behavior test request (development/test only)."""

    camera_id: str = Field(default="test_camera", description="Test camera ID")
    track_id: int = Field(default=1, description="Test track ID")
    behavior_type: BehaviorType = Field(description="Behavior to test")
    severity: BehaviorSeverity = Field(default="MEDIUM", description="Behavior severity")
    duration_seconds: float | None = Field(default=None, description="Duration for loitering/stationary")
    displacement_pixels: float | None = Field(default=None, description="Displacement for movement behaviors")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Detection confidence")


class BehaviorTestResponse(BaseModel):
    """Response from synthetic behavior test endpoint."""

    test_mode: bool = Field(default=True, description="Indicates this is a test response")
    behavior_type: BehaviorType = Field(description="Tested behavior type")
    severity: BehaviorSeverity = Field(description="Resulting severity")
    behavior_score: int = Field(description="Behavior score contribution")
    reason: str = Field(description="Explanation of result")
    input_params: dict = Field(description="Echo of input parameters")
