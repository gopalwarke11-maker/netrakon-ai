"""Stateful intrusion detector and crossing state machine.

Implements:
- Anchor-point extraction (bottom-center)
- Line-side calculation via cross-product orientation
- Jitter / dead-zone suppression
- Intrusion state machine per (camera_id, boundary_id, track_id)
- Deterministic severity mapping
- Integration with alert_service
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from app.ai.geometry import (
    check_boundary_crossing,
    classify_side,
    get_bottom_center_anchor,
    perpendicular_distance,
)
from app.ai.schemas import TrackedObject
from app.models.alert import AlertCreate, AlertSeverity
from app.models.boundary import VirtualBoundary
from app.models.intrusion import (
    CrossingDirection,
    IntrusionEvent,
    IntrusionPoint,
    IntrusionState,
)
from app.services.intrusion_service import intrusion_service
from app.services.alert_websocket import alert_connection_manager
from app.services.camera_service import camera_service

logger = logging.getLogger(__name__)

# Classes considered vehicular threats (upgraded to CRITICAL)
_VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}
# Classes considered low-threat / nuisance (downgraded to LOW)
_ANIMAL_CLASSES = {"dog", "cat", "bird", "horse", "sheep", "cow"}


def calculate_deterministic_severity(
    boundary_severity: AlertSeverity,
    object_class: str,
) -> AlertSeverity:
    """Determine event severity deterministically based on object class and boundary config.

    Rules:
    - Vehicles (car, truck, bus, motorcycle) breaching boundary -> CRITICAL
    - Animals (dog, cat, bird, etc.) -> LOW
    - Persons or standard surveillance objects -> boundary_severity (default HIGH)
    """
    cls_lower = object_class.lower()
    if cls_lower in _VEHICLE_CLASSES:
        return "CRITICAL"
    if cls_lower in _ANIMAL_CLASSES:
        return "LOW"
    return boundary_severity


@dataclass
class TrackBoundaryState:
    """State record for a single track with respect to a single boundary."""
    camera_id: str
    boundary_id: str
    track_id: int
    state: IntrusionState = "SAFE"
    last_anchor: tuple[float, float] | None = None
    last_side: Literal["positive", "negative", "on_line"] = "on_line"
    last_seen_frame: int = 0
    consecutive_frames_inside: int = 0
    alert_emitted: bool = False


class IntrusionDetector:
    """Stateful intrusion detector evaluating active boundaries against tracked objects."""

    def __init__(self, max_idle_frames: int = 300) -> None:
        # Key: (camera_id, boundary_id, track_id)
        self._states: dict[tuple[str, str, int], TrackBoundaryState] = {}
        self._max_idle_frames = max_idle_frames
        self._events: list[IntrusionEvent] = []

    def clear(self) -> None:
        """Reset all tracking states and events (useful for tests)."""
        self._states.clear()
        self._events.clear()

    def clear_camera(self, camera_id: str) -> None:
        """Clear transient state and events owned by one camera only."""
        self._states = {
            key: state for key, state in self._states.items() if state.camera_id != camera_id
        }
        self._events = [event for event in self._events if event.camera_id != camera_id]

    def get_events(self) -> list[IntrusionEvent]:
        """Return all recorded intrusion events."""
        return list(self._events)

    def process_tracks(
        self,
        camera_id: str,
        frame_number: int,
        tracked_objects: list[TrackedObject],
        boundaries: list[VirtualBoundary],
        timestamp: datetime | None = None,
    ) -> list[IntrusionEvent]:
        """Evaluate tracked objects against active boundaries for a given camera frame.

        Args:
            camera_id: Identifier of the camera streaming this frame.
            frame_number: 1-based frame index.
            tracked_objects: List of TrackedObject instances from ByteTrack.
            boundaries: Active boundaries configured for this camera.
            timestamp: Optional frame timestamp; defaults to current UTC.

        Returns:
            List of new IntrusionEvent instances generated in this frame.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        new_events: list[IntrusionEvent] = []
        active_boundaries = [b for b in boundaries if b.enabled and b.camera_id == camera_id]

        if not active_boundaries or not tracked_objects:
            # Clean up old tracks periodically
            self._prune_stale_states(frame_number, camera_id)
            return new_events

        for boundary in active_boundaries:
            for obj in tracked_objects:
                track_id = obj.track_id
                anchor = get_bottom_center_anchor(obj.bounding_box)

                event = self._evaluate_track_boundary(
                    camera_id=camera_id,
                    boundary=boundary,
                    obj=obj,
                    curr_anchor=anchor,
                    frame_number=frame_number,
                    timestamp=timestamp,
                )
                if event is not None:
                    new_events.append(event)

        self._prune_stale_states(frame_number, camera_id)
        return new_events

    def _evaluate_track_boundary(
        self,
        camera_id: str,
        boundary: VirtualBoundary,
        obj: TrackedObject,
        curr_anchor: tuple[float, float],
        frame_number: int,
        timestamp: datetime,
    ) -> IntrusionEvent | None:
        """Evaluate a single track against a single boundary."""
        key = (camera_id, boundary.id, obj.track_id)
        state_rec = self._states.get(key)

        curr_side = classify_side(
            boundary.point_a,
            boundary.point_b,
            curr_anchor,
            tolerance=boundary.tolerance,
        )

        unrestricted_side = "negative" if boundary.restricted_side == "positive" else "positive"

        # First time seeing this track for this boundary
        if state_rec is None:
            initial_state: IntrusionState = "ALERTED" if curr_side == boundary.restricted_side else "SAFE"
            self._states[key] = TrackBoundaryState(
                camera_id=camera_id,
                boundary_id=boundary.id,
                track_id=obj.track_id,
                state=initial_state,
                last_anchor=curr_anchor,
                last_side=curr_side,
                last_seen_frame=frame_number,
                alert_emitted=(initial_state == "ALERTED"),
            )
            # Note: Object appearing already inside the restricted zone on first frame is initialized
            # without triggering crossing event to avoid false alarms from initial detection flicker.
            return None

        prev_anchor = state_rec.last_anchor or curr_anchor
        prev_side = state_rec.last_side

        # Update last seen
        state_rec.last_seen_frame = frame_number
        state_rec.last_anchor = curr_anchor

        # ── State 1: Already ALERTED ───────────────────────────────────────────
        if state_rec.state == "ALERTED":
            # Track is already inside restricted area.
            # Only transition back to SAFE if it firmly crosses back to unrestricted side
            # beyond the deadzone tolerance.
            if curr_side == unrestricted_side:
                dist = perpendicular_distance(boundary.point_a, boundary.point_b, curr_anchor)
                if dist >= boundary.tolerance:
                    logger.info(
                        "Track #%d exited restricted zone for boundary '%s' (State: ALERTED -> SAFE)",
                        obj.track_id,
                        boundary.name,
                    )
                    state_rec.state = "SAFE"
                    state_rec.alert_emitted = False
                    state_rec.last_side = curr_side
            return None

        # ── State 2: SAFE or APPROACHING ──────────────────────────────────────
        # Check geometric crossing
        crossed_into_restricted, direction = check_boundary_crossing(
            a=boundary.point_a,
            b=boundary.point_b,
            prev_point=prev_anchor,
            curr_point=curr_anchor,
            restricted_side=boundary.restricted_side,
            tolerance=boundary.tolerance,
        )

        # Update approach state if close on unrestricted side
        if not crossed_into_restricted:
            dist = perpendicular_distance(boundary.point_a, boundary.point_b, curr_anchor)
            if dist < boundary.tolerance * 2.5 and curr_side != boundary.restricted_side:
                state_rec.state = "APPROACHING"
            else:
                state_rec.state = "SAFE"
            state_rec.last_side = curr_side
            return None

        # ── Crossing Detected! ────────────────────────────────────────────────
        # Must be moving into restricted side
        if crossed_into_restricted and not state_rec.alert_emitted:
            state_rec.state = "ALERTED"
            state_rec.alert_emitted = True
            state_rec.last_side = curr_side

            severity = calculate_deterministic_severity(boundary.severity, obj.class_name)
            # Persist the event and alert atomically before real-time delivery.
            cam = camera_service.get(camera_id)
            sector = cam.sector if cam else "UNASSIGNED"
            alert_msg = (
                f"Intrusion detected: {obj.class_name} (Track #{obj.track_id}) "
                f"crossed boundary '{boundary.name}'"
            )

            event = IntrusionEvent(
                id="PENDING",
                camera_id=camera_id,
                boundary_id=boundary.id,
                boundary_name=boundary.name,
                track_id=obj.track_id,
                object_class=obj.class_name,
                confidence=obj.confidence,
                timestamp=timestamp,
                current_anchor=IntrusionPoint(x=curr_anchor[0], y=curr_anchor[1]),
                previous_anchor=IntrusionPoint(x=prev_anchor[0], y=prev_anchor[1]),
                crossing_direction="UNRESTRICTED_TO_RESTRICTED",
                severity=severity,
                alert_id=None,
                event_type="INTRUSION",
                status="ACTIVE",
            )
            event, created_alert = intrusion_service.create_with_alert(
                event,
                AlertCreate(
                    camera_id=camera_id, sector=sector, type="INTRUSION", severity=severity,
                    message=alert_msg, track_id=str(obj.track_id), confidence=obj.confidence,
                    timestamp=timestamp, status="ACTIVE", boundary_id=boundary.id, source="INTRUSION_DETECTOR",
                ),
            )
            self._events.append(event)
            # Phase 6: only confirmed Phase 5 events are broadcast, after the
            # ordinary REST alert has been created successfully.
            alert_connection_manager.publish_intrusion(event, created_alert)

            logger.warning(
                "INTRUSION DETECTED: Track #%d (%s) crossed boundary '%s' on %s [Alert: %s, Severity: %s]",
                obj.track_id,
                obj.class_name,
                boundary.name,
                camera_id,
                created_alert.id,
                severity,
            )
            return event

        return None

    def _prune_stale_states(self, current_frame: int, camera_id: str) -> None:
        """Remove stale state for this camera without affecting other streams."""
        keys_to_remove = [
            k
            for k, state in self._states.items()
            if state.camera_id == camera_id and (current_frame - state.last_seen_frame) > self._max_idle_frames
        ]
        for k in keys_to_remove:
            del self._states[k]


# Global detector instance
intrusion_detector = IntrusionDetector()
