"""AI Intrusion test endpoint — POST /api/ai/intrusion-test.

Provides a deterministic endpoint to validate boundary crossing geometry,
state machine transitions, jitter suppression, and alert generation without
requiring a real camera or video file.

Clearly labeled as SYNTHETIC / SIMULATION.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.intrusion_detector import IntrusionDetector
from app.ai.schemas import BoundingBoxAI, TrackedObject
from app.models.alert import Alert
from app.models.boundary import (
    Point2D,
    VirtualBoundary,
    VirtualBoundaryCreate,
)
from app.services.alert_service import alert_service
from app.services.boundary_service import boundary_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Intrusion"])


class IntrusionTestTrack(BaseModel):
    """A simulated tracked object within one test frame."""

    track_id: int = Field(description="Track ID of the simulated object")
    class_name: str = Field(default="person", description="COCO class name (e.g. person, car)")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    # Either provide bounding_box or direct anchor_x and anchor_y
    bounding_box: BoundingBoxAI | None = None
    anchor_x: float | None = Field(default=None, description="Direct anchor X coordinate (if bbox omitted)")
    anchor_y: float | None = Field(default=None, description="Direct anchor Y coordinate (if bbox omitted)")


class IntrusionTestFrame(BaseModel):
    """A single sequential frame in a test scenario."""

    frame_number: int = Field(description="1-based frame index")
    timestamp_ms: float = Field(default=0.0, description="Optional frame timestamp offset in ms")
    tracks: list[IntrusionTestTrack] = Field(description="Simulated tracks present in this frame")


class IntrusionTestRequest(BaseModel):
    """Request payload for POST /api/ai/intrusion-test."""

    camera_id: str = Field(description="Camera to evaluate against")
    # Custom test boundary or use registered camera boundaries
    custom_boundary: VirtualBoundaryCreate | None = Field(
        default=None,
        description="Optional ad-hoc boundary to evaluate. If omitted, existing camera boundaries are used.",
    )
    frames: list[IntrusionTestFrame] = Field(
        min_length=1,
        description="Sequential list of frames with simulated tracks to process",
    )


class IntrusionTestResponse(BaseModel):
    """Response payload for POST /api/ai/intrusion-test."""

    is_simulation: bool = Field(default=True, description="Always True for synthetic tests")
    mode: str = Field(default="SYNTHETIC_GEOMETRIC_SIMULATION")
    camera_id: str
    boundaries_evaluated: list[VirtualBoundary]
    frames_evaluated: int
    tracks_evaluated: int
    intrusions_detected: int
    events: list[dict]
    alerts_generated: list[Alert]
    diagnostics: dict


@router.post(
    "/intrusion-test",
    response_model=IntrusionTestResponse,
    summary="Run deterministic intrusion detection test on synthetic tracks",
    description=(
        "Simulate sequential frames and tracked object movements to test geometric crossing "
        "detection, jitter suppression, intrusion state machine, and alert integration.\n\n"
        "**This is a deterministic simulation endpoint.** It does NOT invoke real YOLO inference."
    ),
)
def run_intrusion_test(payload: IntrusionTestRequest) -> IntrusionTestResponse:
    """Execute a deterministic sequence of track positions against virtual boundaries."""
    # Resolve boundaries to test
    boundaries: list[VirtualBoundary] = []
    if payload.custom_boundary is not None:
        bnd_data = payload.custom_boundary.model_dump(exclude={"id"})
        boundaries = [
            VirtualBoundary(
                id=payload.custom_boundary.id or "TEST-BND-01",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                **bnd_data,
            )
        ]
        # Ensure test boundary is persisted to database before detector tries to reference it
        from app.db.session import SessionLocal
        from app.db.models import BoundaryRecord
        with SessionLocal.begin() as db:
            existing = db.query(BoundaryRecord).filter(BoundaryRecord.id == boundaries[0].id).first()
            if not existing:
                rec = BoundaryRecord(
                    id=boundaries[0].id,
                    camera_id=boundaries[0].camera_id,
                    name=boundaries[0].name,
                    enabled=boundaries[0].enabled,
                    point_a=boundaries[0].point_a.model_dump(),
                    point_b=boundaries[0].point_b.model_dump(),
                    restricted_side=boundaries[0].restricted_side,
                    severity=boundaries[0].severity,
                    tolerance=boundaries[0].tolerance,
                    created_at=boundaries[0].created_at,
                    updated_at=boundaries[0].updated_at,
                )
                db.add(rec)
                db.flush()
    else:
        boundaries = boundary_service.get_by_camera(payload.camera_id)
        if not boundaries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"NO BOUNDARY CONFIGURED for camera '{payload.camera_id}'.",
            )

    # Create an isolated detector instance for this test run
    detector = IntrusionDetector()
    all_events = []
    alerts_created: list[Alert] = []
    unique_tracks = set()

    for frame in payload.frames:
        frame_tracks: list[TrackedObject] = []
        for t in frame.tracks:
            unique_tracks.add(t.track_id)
            if t.bounding_box is not None:
                bbox = t.bounding_box
            elif t.anchor_x is not None and t.anchor_y is not None:
                # Synthesize a bounding box that has bottom-center at (anchor_x, anchor_y)
                # width 40, height 80
                w = 40.0
                h = 80.0
                x1 = t.anchor_x - (w / 2.0)
                x2 = t.anchor_x + (w / 2.0)
                y1 = t.anchor_y - h
                y2 = t.anchor_y
                bbox = BoundingBoxAI(x1=x1, y1=y1, x2=x2, y2=y2, width=w, height=h)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Track {t.track_id} in frame {frame.frame_number} must have bounding_box or (anchor_x, anchor_y).",
                )

            cx = (bbox.x1 + bbox.x2) / 2.0
            cy = (bbox.y1 + bbox.y2) / 2.0

            frame_tracks.append(
                TrackedObject(
                    track_id=t.track_id,
                    class_id=0 if t.class_name == "person" else 1,
                    class_name=t.class_name,
                    confidence=t.confidence,
                    bounding_box=bbox,
                    center_x=cx,
                    center_y=cy,
                )
            )

        events = detector.process_tracks(
            camera_id=payload.camera_id,
            frame_number=frame.frame_number,
            tracked_objects=frame_tracks,
            boundaries=boundaries,
        )
        for ev in events:
            all_events.append(ev.model_dump())
            if ev.alert_id:
                alt = alert_service.get(ev.alert_id)
                if alt:
                    alerts_created.append(alt)

    return IntrusionTestResponse(
        is_simulation=True,
        mode="SYNTHETIC_GEOMETRIC_SIMULATION",
        camera_id=payload.camera_id,
        boundaries_evaluated=boundaries,
        frames_evaluated=len(payload.frames),
        tracks_evaluated=len(unique_tracks),
        intrusions_detected=len(all_events),
        events=all_events,
        alerts_generated=alerts_created,
        diagnostics={
            "description": "Simulation completed successfully. One real crossing yields one alert.",
            "duplicate_alerts_suppressed": True,
        },
    )
