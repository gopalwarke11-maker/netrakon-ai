"""Intrusion event and state schemas."""

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

from app.models.alert import AlertSeverity

IntrusionState = Literal["SAFE", "APPROACHING", "CROSSED", "ALERTED"]
CrossingDirection = Literal[
    "UNRESTRICTED_TO_RESTRICTED",
    "RESTRICTED_TO_UNRESTRICTED",
    "NONE",
]


class IntrusionPoint(BaseModel):
    """Anchor coordinate in pixels."""
    x: float
    y: float


class IntrusionEvent(BaseModel):
    """Record of a confirmed security boundary crossing event."""
    id: str = Field(description="Unique event ID (e.g. EVT-0001)")
    camera_id: str = Field(description="Camera where intrusion occurred")
    boundary_id: str = Field(description="Boundary that was crossed")
    boundary_name: str = Field(description="Name of the crossed boundary")
    track_id: int = Field(description="Track ID of the intruding object")
    object_class: str = Field(description="COCO class name (e.g. person, car)")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_anchor: IntrusionPoint = Field(description="Bottom-center position at crossing")
    previous_anchor: IntrusionPoint = Field(description="Bottom-center position before crossing")
    crossing_direction: CrossingDirection = Field(description="Direction of crossing relative to restricted zone")
    severity: AlertSeverity = Field(description="Assigned severity based on boundary & object rules")
    alert_id: str | None = Field(default=None, description="Linked system alert ID if registered")
    event_type: str = Field(default="INTRUSION", description="Event category")
    status: str = Field(default="ACTIVE", description="Event status")
