"""Detection request and response schemas."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class DetectionBase(BaseModel):
    camera_id: str = Field(min_length=1, max_length=80)
    object_type: str = Field(min_length=1, max_length=80)
    confidence: float = Field(ge=0, le=1)
    track_id: str | None = Field(default=None, max_length=80)
    bounding_box: BoundingBox
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DetectionCreate(DetectionBase):
    pass


class Detection(DetectionBase):
    id: str