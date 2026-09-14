"""Phase 12 process-restart persistence and database-backed idempotency tests."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete

from app.ai.behavior_schemas import BehaviorAssessment, BehaviorObservationSchema
from app.db.models import (
    AlertRecord,
    BehaviorObservationRecord,
    BoundaryRecord,
    CameraRecord,
    IntrusionEventRecord,
)
from app.db.session import SessionLocal
from app.models.alert import AlertCreate
from app.models.intrusion import IntrusionEvent, IntrusionPoint
from app.services.behavior_service import behavior_service
from app.services.intrusion_service import intrusion_service


def _assessment(camera_id: str, track_id: int, behavior_type: str = "STATIONARY", score: int = 5) -> BehaviorAssessment:
    now = datetime.now(timezone.utc)
    return BehaviorAssessment(
        id=f"BEH-RESTART-{uuid4().hex}",
        camera_id=camera_id,
        track_id=track_id,
        observations=[BehaviorObservationSchema(
            behavior_type=behavior_type,
            severity="LOW",
            confidence=0.8,
            evidence={"frames": 10.0},
            reason=f"Restart persistence {behavior_type}.",
            detected_at=now,
        )],
        behavior_score=score,
        primary_behavior=behavior_type,
        assessed_at=now,
        duration_window_seconds=1.0,
        created_at=now,
    )


def _wait_for_http(port: int, path: str, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"Server did not become available: {last_error}")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _cleanup_records(camera_id: str, boundary_id: str, event_id: str, alert_id: str, behavior_ids: list[str]) -> None:
    with SessionLocal.begin() as db:
        if behavior_ids:
            db.execute(delete(BehaviorObservationRecord).where(BehaviorObservationRecord.id.in_(behavior_ids)))
        db.execute(delete(AlertRecord).where(AlertRecord.id == alert_id))
        db.execute(delete(IntrusionEventRecord).where(IntrusionEventRecord.id == event_id))
        db.execute(delete(BoundaryRecord).where(BoundaryRecord.id == boundary_id))
        db.execute(delete(CameraRecord).where(CameraRecord.id == camera_id))


def test_behavior_idempotency_survives_worker_restart_without_migration():
    camera_id = "CAM-01"
    track_id = 910001
    first = _assessment(camera_id, track_id)
    second = _assessment(camera_id, track_id)
    different = _assessment(camera_id, track_id, behavior_type="RAPID_MOVEMENT", score=15)
    created_ids: list[str] = []
    try:
        first_result = behavior_service.create_behavior(first)
        second_result = behavior_service.create_behavior(second)
        different_result = behavior_service.create_behavior(different)
        assert first_result is not None
        assert second_result is not None
        assert different_result is not None
        assert second_result.id == first_result.id
        assert different_result.id != first_result.id
        created_ids.extend([first_result.id, different_result.id])

        records = behavior_service.get_track_behaviors(camera_id, track_id)
        assert len(records) == 2
        assert {record.primary_behavior for record in records} == {"STATIONARY", "RAPID_MOVEMENT"}
    finally:
        with SessionLocal.begin() as db:
            db.execute(delete(BehaviorObservationRecord).where(BehaviorObservationRecord.id.in_(created_ids)))


def test_same_track_id_remains_isolated_by_camera_after_restart():
    first_camera = "CAM-01"
    second_camera = "CAM-02"
    first = _assessment(first_camera, 910002)
    second = _assessment(second_camera, 910002)
    try:
        assert behavior_service.create_behavior(first) is not None
        assert behavior_service.create_behavior(second) is not None
        assert len(behavior_service.get_track_behaviors(first_camera, 910002)) == 1
        assert len(behavior_service.get_track_behaviors(second_camera, 910002)) == 1
    finally:
        with SessionLocal.begin() as db:
            db.execute(delete(BehaviorObservationRecord).where(
                BehaviorObservationRecord.camera_id.in_([first_camera, second_camera])
                , BehaviorObservationRecord.track_id == 910002
            ))


def test_different_track_ids_remain_distinct_behavior_states():
    camera_id = "CAM-01"
    first = _assessment(camera_id, 910004)
    second = _assessment(camera_id, 910005)
    created_ids: list[str] = []
    try:
        first_result = behavior_service.create_behavior(first)
        second_result = behavior_service.create_behavior(second)
        assert first_result is not None and second_result is not None
        created_ids.extend([first_result.id, second_result.id])
        records = behavior_service.get_camera_behaviors(camera_id)
        assert {record.track_id for record in records if record.track_id in {910004, 910005}} == {910004, 910005}
    finally:
        with SessionLocal.begin() as db:
            db.execute(delete(BehaviorObservationRecord).where(BehaviorObservationRecord.id.in_(created_ids)))


def test_actual_application_process_restart_preserves_records_and_relationships():
    suffix = uuid4().hex[:12]
    camera_id = f"CAM-RESTART-{suffix}"
    boundary_id = f"BND-RESTART-{suffix}"
    track_id = 910003
    event_id = ""
    alert_id = ""
    behavior_ids: list[str] = []
    port = _free_port()
    child: subprocess.Popen[str] | None = None

    try:
        with SessionLocal.begin() as db:
            db.add(CameraRecord(
                id=camera_id,
                name="Phase 12 restart camera",
                sector="PHASE12",
                location="Deterministic restart validation",
                status="ONLINE",
                stream_url=None,
            ))
            db.add(BoundaryRecord(
                id=boundary_id,
                camera_id=camera_id,
                name="Phase 12 restart boundary",
                enabled=True,
                point_a={"x": 100.0, "y": 300.0},
                point_b={"x": 800.0, "y": 300.0},
                restricted_side="positive",
                severity="HIGH",
                tolerance=5.0,
            ))

        event = IntrusionEvent(
            id="PENDING",
            camera_id=camera_id,
            boundary_id=boundary_id,
            boundary_name="Phase 12 restart boundary",
            track_id=track_id,
            object_class="person",
            confidence=0.91,
            timestamp=datetime.now(timezone.utc),
            previous_anchor=IntrusionPoint(x=90, y=300),
            current_anchor=IntrusionPoint(x=110, y=300),
            crossing_direction="UNRESTRICTED_TO_RESTRICTED",
            severity="HIGH",
        )
        persisted_event, persisted_alert = intrusion_service.create_with_alert(
            event,
            AlertCreate(
                camera_id=camera_id,
                sector="PHASE12",
                type="INTRUSION",
                severity="HIGH",
                message="Phase 12 restart persistence event",
                track_id=str(track_id),
                confidence=0.91,
                timestamp=event.timestamp,
                status="ACTIVE",
                boundary_id=boundary_id,
                source="PHASE12_TEST",
            ),
        )
        event_id = persisted_event.id
        alert_id = persisted_alert.id
        behavior = _assessment(camera_id, track_id)
        behavior.intrusion_event_id = event_id
        persisted_behavior = behavior_service.create_behavior(behavior)
        assert persisted_behavior is not None
        behavior_ids.append(persisted_behavior.id)

        environment = os.environ.copy()
        command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
        child = subprocess.Popen(command, cwd=os.path.dirname(__file__), env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _wait_for_http(port, "/api/health")

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/cameras/{camera_id}", timeout=10) as response:
            camera_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/cameras/{camera_id}/boundaries", timeout=10) as response:
            boundaries_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/alerts?camera_id={camera_id}", timeout=10) as response:
            alerts_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/intrusions?camera_id={camera_id}", timeout=10) as response:
            intrusions_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ai/behavior/camera/{camera_id}", timeout=10) as response:
            behaviors_payload = json.loads(response.read().decode("utf-8"))

        assert camera_payload["id"] == camera_id
        assert boundaries_payload[0]["id"] == boundary_id
        assert boundaries_payload[0]["camera_id"] == camera_id
        assert any(item["id"] == alert_id and item["camera_id"] == camera_id for item in alerts_payload)
        assert any(item["id"] == event_id and item["camera_id"] == camera_id for item in intrusions_payload)
        assert any(item["camera_id"] == camera_id and item["track_id"] == track_id for item in behaviors_payload)

        with SessionLocal() as db:
            event_row = db.get(IntrusionEventRecord, event_id)
            alert_row = db.get(AlertRecord, alert_id)
            behavior_row = db.get(BehaviorObservationRecord, persisted_behavior.id)
            assert event_row is not None and event_row.risk_score is not None and event_row.risk_level is not None
            assert event_row.risk_factors
            assert alert_row is not None and alert_row.risk_score is not None and alert_row.risk_level is not None
            assert behavior_row is not None and behavior_row.intrusion_event_id == event_id
    finally:
        if child is not None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=15)
        if event_id:
            _cleanup_records(camera_id, boundary_id, event_id, alert_id, behavior_ids)
        else:
            with SessionLocal.begin() as db:
                db.execute(delete(BoundaryRecord).where(BoundaryRecord.id == boundary_id))
                db.execute(delete(CameraRecord).where(CameraRecord.id == camera_id))
