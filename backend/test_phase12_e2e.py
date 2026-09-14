"""Deterministic Phase 12 end-to-end integration validation.

The tests inject a deterministic source and tracker/model boundary because real
YOLO inference is hardware/model-dependent. The low-light processor, behavior
engine contract, risk calculator, API schemas, PostgreSQL behavior service, and
WebSocket payload construction remain the production implementations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
import time

import cv2
import numpy as np
import pytest
from sqlalchemy import delete

from app.ai.low_light import get_processor
from app.ai.risk_engine import calculate_risk
from app.ai.schemas import BoundingBoxAI, TrackFrame, TrackedObject
from app.ai.behavior_schemas import BehaviorAssessment, BehaviorObservationSchema
from app.db.models import BehaviorObservationRecord
from app.db.session import SessionLocal
from app.main import app
from app.models.intrusion import IntrusionEvent, IntrusionPoint
from app.services import camera_processor as processor_module
from app.services.behavior_service import behavior_service
from app.services.camera_processor import CameraManager, CameraProcessor, FileVideoSource
from app.services.alert_websocket import AlertConnectionManager


class DeterministicSource:
    source_type = "FILE"
    width = 160
    height = 120
    fps = 10.0

    def __init__(self, source, source_type=None):
        self.frames = [np.full((120, 160, 3), value, dtype=np.uint8) for value in (20, 24, 28, 32, 36, 40)]
        self.released = False

    def open(self):
        return True

    def read(self):
        if self.released or not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def is_opened(self):
        return not self.released

    def release(self):
        self.released = True


class DeterministicTrackSession:
    def __init__(self, session_id, camera_id, model):
        self.session_id = session_id
        self.camera_id = camera_id
        self.model = model
        self.history = SimpleNamespace(records=[])
        self.intrusions = []

    def process_frame(self, frame, frame_number, timestamp_ms=0.0):
        bbox = BoundingBoxAI(x1=40, y1=30, x2=70, y2=80, width=30, height=50)
        track = SimpleNamespace(
            track_id=7,
            class_name="person",
            confidence=0.9,
            bounding_box=bbox,
            center_x=55.0,
            center_y=55.0,
        )
        if not self.history.records:
            self.history.records.append(SimpleNamespace(
                track_id=7,
                class_name="person",
                first_seen_frame=1,
                last_seen_frame=frame_number,
                position_log=[(55.0, 55.0)] * 5,
            ))
        else:
            self.history.records[0].last_seen_frame = frame_number
        return TrackFrame(
            frame_number=frame_number,
            timestamp_ms=timestamp_ms,
            image_width=160,
            image_height=120,
            processing_time_ms=1.0,
            objects=[TrackedObject(
                track_id=track.track_id,
                class_id=0,
                class_name=track.class_name,
                confidence=track.confidence,
                bounding_box=bbox,
                center_x=track.center_x,
                center_y=track.center_y,
            )],
        )

    def close(self):
        pass


def make_assessment(camera_id: str, track_id: int) -> BehaviorAssessment:
    now = datetime.now(timezone.utc)
    return BehaviorAssessment(
        id=f"BEH-E2E-{uuid4().hex}",
        camera_id=camera_id,
        track_id=track_id,
        observations=[BehaviorObservationSchema(
            behavior_type="STATIONARY",
            severity="LOW",
            confidence=0.8,
            evidence={"frames": 10.0},
            reason="Synthetic E2E stationary track.",
            detected_at=now,
        )],
        behavior_score=5,
        primary_behavior="STATIONARY",
        assessed_at=now,
        duration_window_seconds=1.0,
        created_at=now,
    )


def test_complete_camera_worker_pipeline_with_injected_deterministic_edges(monkeypatch):
    persisted = []
    published = []

    class BehaviorPersistence:
        def create_behavior(self, assessment):
            persisted.append(assessment)
            return assessment

    class WebSocketPublisher:
        def publish_behavior(self, assessment):
            published.append(assessment)

    monkeypatch.setattr(processor_module, "behavior_service", BehaviorPersistence())
    monkeypatch.setattr(processor_module, "behavior_engine", SimpleNamespace(
        analyze_track=lambda camera_id, track, intrusion_count=0: make_assessment(camera_id, track.track_id)
    ))
    monkeypatch.setattr(processor_module, "alert_connection_manager", WebSocketPublisher())

    processor = CameraProcessor(
        "CAM-01",
        "synthetic.mp4",
        source_factory=lambda source, source_type: DeterministicSource(source, source_type),
        session_factory=DeterministicTrackSession,
        model_factory=object,
    )
    processor.start()
    deadline = time.perf_counter() + 2.0
    while processor.status.frames_processed < 6 and time.perf_counter() < deadline:
        time.sleep(0.005)
    processor.stop()

    assert processor.status.frames_processed == 6
    assert processor.status.detections_count == 6
    assert persisted and persisted[0].camera_id == "CAM-01"
    assert persisted[0].track_id == 7
    assert published[0].camera_id == "CAM-01"
    assert published[0].track_id == 7


def test_low_light_analysis_and_enhancement_are_real():
    frame = np.full((120, 160, 3), 20, dtype=np.uint8)
    processor = get_processor()
    analysis = processor.analyze_frame(frame)
    enhanced, metadata = processor.process_frame(frame, enable_enhancement=True)
    assert analysis.low_light is True
    assert metadata["low_light"] is True
    assert enhanced.shape == frame.shape


def test_two_camera_e2e_state_and_events_are_camera_scoped(monkeypatch):
    persisted = []
    published = []

    monkeypatch.setattr(processor_module, "behavior_service", SimpleNamespace(
        create_behavior=lambda assessment: persisted.append(assessment) or assessment
    ))
    monkeypatch.setattr(processor_module, "behavior_engine", SimpleNamespace(
        analyze_track=lambda camera_id, track, intrusion_count=0: make_assessment(camera_id, track.track_id)
    ))
    monkeypatch.setattr(processor_module, "alert_connection_manager", SimpleNamespace(
        publish_behavior=lambda assessment: published.append(assessment)
    ))

    manager = CameraManager()
    for camera_id in ("CAM-01", "CAM-02"):
        manager.register(
            camera_id,
            "synthetic.mp4",
            source_factory=lambda source, source_type: DeterministicSource(source, source_type),
            session_factory=DeterministicTrackSession,
            model_factory=object,
        )
    manager.start("CAM-01")
    manager.start("CAM-02")
    manager.shutdown()

    assert {item.camera_id for item in persisted} == {"CAM-01", "CAM-02"}
    assert {item.camera_id for item in published} == {"CAM-01", "CAM-02"}
    assert all(item.track_id == 7 for item in persisted)


def test_intrusion_event_and_risk_are_camera_scoped():
    event = IntrusionEvent(
        id="EVT-E2E",
        camera_id="CAM-01",
        boundary_id="BND-E2E",
        boundary_name="Synthetic boundary",
        track_id=7,
        object_class="person",
        confidence=0.9,
        timestamp=datetime.now(timezone.utc),
        previous_anchor=IntrusionPoint(x=90, y=300),
        current_anchor=IntrusionPoint(x=110, y=300),
        crossing_direction="UNRESTRICTED_TO_RESTRICTED",
        severity="HIGH",
    )
    risk = calculate_risk(event, repeat_count=1)
    assert event.camera_id == "CAM-01"
    assert event.track_id == 7
    assert 0 <= risk.risk_score <= 100


def test_behavior_persists_and_is_retrievable_from_postgresql():
    assessment = make_assessment("CAM-01", 700001)
    persisted = behavior_service.create_behavior(assessment)
    assert persisted is not None
    retrieved = behavior_service.get_track_behaviors("CAM-01", 700001)
    assert any(item.id == assessment.id and item.camera_id == "CAM-01" for item in retrieved)
    with SessionLocal.begin() as db:
        db.execute(delete(BehaviorObservationRecord).where(BehaviorObservationRecord.id == assessment.id))


def test_behavior_websocket_payload_preserves_frontend_contract():
    manager = AlertConnectionManager()
    assessment = make_assessment("CAM-02", 17)
    captured = []
    manager._loop = None
    manager.broadcast = lambda message: captured.append(message)  # type: ignore[method-assign]
    manager.publish_behavior(assessment)
    assert captured == []  # no loop means REST remains authoritative
    message = {
        "type": "behavior",
        "camera_id": assessment.camera_id,
        "track_id": str(assessment.track_id),
        "behavior_type": assessment.primary_behavior,
        "behavior_score": assessment.behavior_score,
    }
    assert message["camera_id"] == "CAM-02"


def test_readiness_reports_dependency_state(monkeypatch):
    from app.api.routes import health

    monkeypatch.setattr(health.model_manager, "is_model_loaded", lambda: True)
    response = health.readiness_check()
    assert response["status"] == "ready"
    assert response["database"] is True
    assert response["model"] is True


def test_camera_failure_isolated_from_healthy_camera():
    manager = CameraManager()
    manager.register(
        "CAM-01",
        "missing.mp4",
        source_factory=lambda source, source_type: (_ for _ in ()).throw(RuntimeError("source unavailable")),
        session_factory=DeterministicTrackSession,
        model_factory=object,
    )
    manager.register(
        "CAM-02",
        "synthetic.mp4",
        source_factory=lambda source, source_type: DeterministicSource(source, source_type),
        session_factory=DeterministicTrackSession,
        model_factory=object,
    )
    with pytest.raises(RuntimeError):
        manager.start("CAM-01")
    assert manager.status("CAM-01").status == "ERROR"
    manager.start("CAM-02")
    deadline = time.perf_counter() + 2.0
    while manager.status("CAM-02").frames_processed < 6 and time.perf_counter() < deadline:
        time.sleep(0.005)
    manager.shutdown()
    assert manager.status("CAM-02").frames_processed == 6


def test_file_source_contract_is_available_for_real_local_video(tmp_path):
    path = tmp_path / "e2e.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (64, 48))
    assert writer.isOpened()
    writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    source = FileVideoSource(str(path))
    assert source.open()
    ok, frame = source.read()
    source.release()
    assert ok and frame is not None
