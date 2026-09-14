"""Alert request and response schemas."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


AlertSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AlertStatus = Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"]


class AlertBase(BaseModel):
    camera_id: str = Field(min_length=1, max_length=80)
    sector: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=80)
    severity: AlertSeverity = "LOW"
    message: str = Field(min_length=1, max_length=1000)
    track_id: str | None = Field(default=None, max_length=80)
    confidence: float | None = Field(default=None, ge=0, le=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: AlertStatus = "ACTIVE"
    boundary_id: str | None = Field(default=None, max_length=80)
    event_id: str | None = Field(default=None, max_length=80)
    source: str = Field(default="SYSTEM", max_length=80)


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    message: str | None = Field(default=None, min_length=1, max_length=1000)
