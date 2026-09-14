"""Schemas for camera processing lifecycle and runtime metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ai.schemas import TrackSummaryEntry, TrackedObject


CameraRuntimeState = Literal[
    "OFFLINE", "CONNECTING", "RECONNECTING", "ONLINE", "PROCESSING", "ERROR", "STOPPED"
]
CameraSourceType = Literal["FILE", "RTSP", "MJPEG", "DEVICE"]


class CameraProcessingStatus(BaseModel):
    camera_id: str
    status: CameraRuntimeState
    source_type: CameraSourceType
    resolution: str | None = None
    fps: float = 0.0
    last_frame_time: datetime | None = None
    frames_processed: int = 0
    detections_count: int = 0
    active_tracks: int = 0
    processing_fps: float = 0.0
    error: str | None = None
    loop_enabled: bool = False


class CameraRuntimeSummary(BaseModel):
    camera_id: str
    status: CameraRuntimeState
    source_type: CameraSourceType
    current_detections: list[TrackedObject] = Field(default_factory=list)
    historical_tracks: list[TrackSummaryEntry] = Field(default_factory=list)
    detection_class_counts: dict[str, int] = Field(default_factory=dict)
    total_detections: int = 0
    average_confidence: float | None = None
    intrusions: list[dict] = Field(default_factory=list)
    last_frame_time: datetime | None = None


class CameraSourceUpdate(BaseModel):
    source: str | int | None = Field(default=None, description="Optional source override for this run")
    source_type: CameraSourceType | None = None
    loop: bool = Field(default=False, description="Reopen local file sources at EOF")
