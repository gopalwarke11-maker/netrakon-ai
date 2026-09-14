"""Deterministic multi-camera alert pipeline coverage."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ai.intrusion_detector import IntrusionDetector
from app.ai.schemas import BoundingBoxAI, TrackedObject
from app.main import app
from app.models.alert import Alert, AlertCreate
from app.models.boundary import Point2D, VirtualBoundary
from app.models.intrusion import IntrusionEvent
from app.models.intrusion import IntrusionPoint
from app.services.intrusion_service import intrusion_service


def boundary(camera_id: str, boundary_id: str) -> VirtualBoundary:
    return VirtualBoundary(
        id=boundary_id,
        camera_id=camera_id,
        name=f"{camera_id} boundary",
        enabled=True,
        point_a=Point2D(x=100, y=300),
        point_b=Point2D(x=700, y=300),
        restricted_side="positive",
        severity="HIGH",
        tolerance=5,
    )


def track(track_id: int, anchor_y: float) -> TrackedObject:
    bbox = BoundingBoxAI(
        x1=380, y1=anchor_y - 80, x2=420, y2=anchor_y,
        width=40, height=80,
    )
    return TrackedObject(
        track_id=track_id,
        class_id=0,
        class_name="person",
        confidence=0.9,
        bounding_box=bbox,
        center_x=400,
        center_y=anchor_y - 40,
    )


def test_same_track_id_isolated_across_four_cameras(monkeypatch):
    persisted: list[tuple[str, str, int]] = []
    published: list[str] = []

    def persist(event: IntrusionEvent, _payload):
        alert = Alert(
            id=f"ALT-{event.camera_id}", event_id=f"EVT-{event.camera_id}",
            camera_id=event.camera_id, sector=event.camera_id, type="INTRUSION",
            severity=event.severity, message="crossing", track_id=str(event.track_id),
            confidence=event.confidence, boundary_id=event.boundary_id,
            source="TEST", status="ACTIVE", timestamp=event.timestamp,
        )
        persisted.append((event.camera_id, event.boundary_id, event.track_id))
        return event.model_copy(update={"id": alert.event_id, "alert_id": alert.id}), alert

    monkeypatch.setattr("app.ai.intrusion_detector.intrusion_service.create_with_alert", persist)
    monkeypatch.setattr("app.ai.intrusion_detector.camera_service.get", lambda camera_id: SimpleNamespace(sector=camera_id))
    monkeypatch.setattr(
        "app.ai.intrusion_detector.alert_connection_manager.publish_intrusion",
        lambda event, _alert: published.append(event.camera_id),
    )

    detector = IntrusionDetector()
    camera_ids = ["CAM-01", "CAM-02", "CAM-03", "CAM-04"]
    for index, camera_id in enumerate(camera_ids):
        bnd = boundary(camera_id, f"BND-{camera_id}")
        detector.process_tracks(camera_id, 1, [track(7, 200)], [bnd])
        events = detector.process_tracks(camera_id, 2, [track(7, 380)], [bnd])
        assert len(events) == 1
        assert events[0].camera_id == camera_id

    assert persisted == [(camera_id, f"BND-{camera_id}", 7) for camera_id in camera_ids]
    assert published == camera_ids


def test_duplicate_crossing_is_suppressed_per_camera_boundary_and_track(monkeypatch):
    created = []
    monkeypatch.setattr(
        "app.ai.intrusion_detector.intrusion_service.create_with_alert",
        lambda event, _payload: (
            created.append(event),
            (event, SimpleNamespace(id="ALT-1", message="crossing", sector="S1", status="ACTIVE")),
        )[1],
    )
    monkeypatch.setattr("app.ai.intrusion_detector.camera_service.get", lambda _camera_id: SimpleNamespace(sector="S1"))
    monkeypatch.setattr("app.ai.intrusion_detector.alert_connection_manager.publish_intrusion", lambda *_args: None)

    detector = IntrusionDetector()
    bnd = boundary("CAM-02", "BND-02")
    detector.process_tracks("CAM-02", 1, [track(7, 200)], [bnd])
    assert len(detector.process_tracks("CAM-02", 2, [track(7, 380)], [bnd])) == 1
    assert len(detector.process_tracks("CAM-02", 3, [track(7, 400)], [bnd])) == 0
    assert len(created) == 1


def test_no_boundary_configured_is_truthful():
    client = TestClient(app)
    response = client.post(
        "/api/ai/intrusion-test",
        json={
            "camera_id": "CAM-03",
            "frames": [{"frame_number": 1, "tracks": []}],
        },
    )
    assert response.status_code == 400
    assert "NO BOUNDARY CONFIGURED" in response.json()["detail"]


def test_postgresql_alert_camera_id_is_preserved_for_two_cameras():
    timestamp = datetime.now(timezone.utc)
    persisted = []
    for camera_id, boundary_id in (("CAM-01", "BND-C1"), ("CAM-02", "BND-C2")):
        event = IntrusionEvent(
            id="PENDING", camera_id=camera_id, boundary_id=boundary_id,
            boundary_name=f"{camera_id} boundary", track_id=77,
            object_class="person", confidence=0.9, timestamp=timestamp,
            previous_anchor=IntrusionPoint(x=400, y=200),
            current_anchor=IntrusionPoint(x=400, y=380),
            crossing_direction="UNRESTRICTED_TO_RESTRICTED", severity="HIGH",
        )
        saved_event, saved_alert = intrusion_service.create_with_alert(
            event,
            AlertCreate(
                camera_id=camera_id, sector=f"SECTOR {camera_id[-2:]}",
                type="INTRUSION", severity="HIGH", message="test crossing",
                track_id="77", confidence=0.9, timestamp=timestamp,
                status="ACTIVE", boundary_id=boundary_id, source="TEST",
            ),
        )
        persisted.append((saved_event.camera_id, saved_alert.camera_id))

    assert persisted == [("CAM-01", "CAM-01"), ("CAM-02", "CAM-02")]
