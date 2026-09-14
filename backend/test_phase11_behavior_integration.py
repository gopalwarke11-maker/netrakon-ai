"""Phase 11 live behavior-engine integration tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import app.services.camera_processor as processor_module
from app.api.routes import ai_behavior
from app.ai.behavior_schemas import BehaviorAssessment, BehaviorObservationSchema
from app.services.camera_processor import CameraProcessor


class FakeHistory:
    def __init__(self, tracks):
        self.records = tracks


class FakeSession:
    def __init__(self, tracks):
        self.history = FakeHistory(tracks)
        self.intrusions = []


class FakeBehaviorEngine:
    def __init__(self):
        self.calls = []
        self.fail_for = set()

    def analyze_track(self, camera_id, track, intrusion_count=1):
        self.calls.append((camera_id, track.track_id, intrusion_count))
        if track.track_id in self.fail_for:
            raise RuntimeError("behavior failure")
        now = datetime.now(timezone.utc)
        return BehaviorAssessment(
            id=f"BEH-{camera_id}-{track.track_id}",
            camera_id=camera_id,
            track_id=track.track_id,
            observations=[BehaviorObservationSchema(
                behavior_type="STATIONARY",
                severity="LOW",
                confidence=0.8,
                evidence={"frames": 10.0},
                reason="Track remained within the stationary threshold.",
                detected_at=now,
            )],
            behavior_score=5,
            primary_behavior="STATIONARY",
            assessed_at=now,
            duration_window_seconds=1.0,
            created_at=now,
        )


def make_processor(camera_id, track_ids=(7,)):
    processor = CameraProcessor(camera_id, "sample.mp4")
    processor._session = FakeSession([SimpleNamespace(track_id=track_id) for track_id in track_ids])
    processor._persisted_behavior_keys.clear()
    return processor


def install_fakes(monkeypatch):
    engine = FakeBehaviorEngine()
    persisted = []
    published = []

    class FakeBehaviorService:
        def create_behavior(self, assessment):
            persisted.append(assessment)
            return assessment

    class FakeWebSocketManager:
        def publish_behavior(self, assessment):
            published.append(assessment)

    monkeypatch.setattr(processor_module, "behavior_engine", engine)
    monkeypatch.setattr(processor_module, "behavior_service", FakeBehaviorService())
    monkeypatch.setattr(processor_module, "alert_connection_manager", FakeWebSocketManager())
    return engine, persisted, published


def test_camera_worker_invokes_existing_behavior_engine(monkeypatch):
    engine, _, _ = install_fakes(monkeypatch)
    processor = make_processor("CAM-01")
    processor._analyze_behaviors()
    assert engine.calls == [("CAM-01", 7, 0)]


def test_behavior_observation_is_persisted(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    make_processor("CAM-01")._analyze_behaviors()
    assert len(persisted) == 1
    assert persisted[0].primary_behavior == "STATIONARY"


def test_behavior_preserves_camera_id(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    make_processor("CAM-01")._analyze_behaviors()
    assert persisted[0].camera_id == "CAM-01"


def test_behavior_preserves_track_id(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    make_processor("CAM-01", track_ids=(17,))._analyze_behaviors()
    assert persisted[0].track_id == 17


def test_same_track_id_on_two_cameras_is_independent(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    make_processor("CAM-01", track_ids=(7,))._analyze_behaviors()
    make_processor("CAM-02", track_ids=(7,))._analyze_behaviors()
    assert [(item.camera_id, item.track_id) for item in persisted] == [("CAM-01", 7), ("CAM-02", 7)]


def test_behavior_state_is_camera_scoped(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    first = make_processor("CAM-01")
    second = make_processor("CAM-02")
    first._analyze_behaviors()
    first._analyze_behaviors()
    second._analyze_behaviors()
    assert len(persisted) == 2
    assert first._persisted_behavior_keys != second._persisted_behavior_keys


def test_restart_reset_does_not_touch_other_camera_state(monkeypatch):
    install_fakes(monkeypatch)
    first = make_processor("CAM-01")
    second = make_processor("CAM-02")
    first._persisted_behavior_keys.add(("CAM-01", 7, "STATIONARY", 5))
    second._persisted_behavior_keys.add(("CAM-02", 7, "STATIONARY", 5))
    first._persisted_behavior_keys.clear()
    assert not first._persisted_behavior_keys
    assert second._persisted_behavior_keys == {("CAM-02", 7, "STATIONARY", 5)}


def test_duplicate_behavior_state_does_not_spam_persistence(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    processor = make_processor("CAM-01")
    processor._analyze_behaviors()
    processor._analyze_behaviors()
    processor._analyze_behaviors()
    assert len(persisted) == 1


def test_changed_behavior_score_is_persisted(monkeypatch):
    engine, persisted, _ = install_fakes(monkeypatch)
    processor = make_processor("CAM-01")
    processor._analyze_behaviors()
    original = engine.analyze_track
    engine.analyze_track = lambda camera_id, track, intrusion_count=1: original(camera_id, track, intrusion_count).model_copy(update={"behavior_score": 10})
    processor._analyze_behaviors()
    assert len(persisted) == 2


def test_websocket_behavior_event_preserves_camera_and_track(monkeypatch):
    _, _, published = install_fakes(monkeypatch)
    make_processor("CAM-01", track_ids=(17,))._analyze_behaviors()
    assert published[0].camera_id == "CAM-01"
    assert published[0].track_id == 17
    assert published[0].behavior_score == 5


def test_behavior_failure_does_not_stop_other_tracks(monkeypatch):
    engine, persisted, _ = install_fakes(monkeypatch)
    engine.fail_for.add(7)
    processor = make_processor("CAM-01", track_ids=(7, 8))
    processor._analyze_behaviors()
    assert len(persisted) == 1
    assert persisted[0].track_id == 8


def test_behavior_failure_does_not_cross_camera_boundary(monkeypatch):
    engine, persisted, _ = install_fakes(monkeypatch)
    engine.fail_for.add(7)
    make_processor("CAM-01", track_ids=(7,))._analyze_behaviors()
    make_processor("CAM-02", track_ids=(8,))._analyze_behaviors()
    assert [(item.camera_id, item.track_id) for item in persisted] == [("CAM-02", 8)]


def test_existing_database_behavior_is_not_republished(monkeypatch):
    engine, persisted, published = install_fakes(monkeypatch)
    processor = make_processor("CAM-01")
    original = engine.analyze_track
    existing = original("CAM-01", processor._session.history.records[0], 0).model_copy(
        update={"id": "BEH-EXISTING"}
    )

    class ExistingBehaviorService:
        def create_behavior(self, assessment):
            return existing

    monkeypatch.setattr(processor_module, "behavior_service", ExistingBehaviorService())
    processor._analyze_behaviors()
    assert not persisted
    assert not published


def test_behavior_type_and_evidence_are_preserved(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    make_processor("CAM-01")._analyze_behaviors()
    assert persisted[0].observations[0].behavior_type == "STATIONARY"
    assert persisted[0].observations[0].evidence == {"frames": 10.0}
    assert "stationary" in persisted[0].observations[0].reason.lower()


def test_behavior_engine_receives_intrusion_count(monkeypatch):
    engine, _, _ = install_fakes(monkeypatch)
    processor = make_processor("CAM-01")
    processor._session.intrusions = [SimpleNamespace(camera_id="CAM-01", track_id=7)]
    processor._analyze_behaviors()
    assert engine.calls == [("CAM-01", 7, 1)]


def test_other_camera_intrusion_is_not_counted(monkeypatch):
    engine, _, _ = install_fakes(monkeypatch)
    processor = make_processor("CAM-01")
    processor._session.intrusions = [SimpleNamespace(camera_id="CAM-02", track_id=7)]
    processor._analyze_behaviors()
    assert engine.calls == [("CAM-01", 7, 0)]


def test_behavior_api_retrieves_camera_scoped_worker_observation(monkeypatch):
    _, persisted, _ = install_fakes(monkeypatch)
    make_processor("CAM-01", track_ids=(17,))._analyze_behaviors()

    class FakeBehaviorService:
        def get_camera_behaviors(self, camera_id, limit=100):
            return [item for item in persisted if item.camera_id == camera_id][:limit]

    monkeypatch.setattr(ai_behavior, "behavior_service", FakeBehaviorService())
    result = ai_behavior.get_camera_behaviors("CAM-01", limit=10)
    assert len(result) == 1
    assert result[0].camera_id == "CAM-01"
    assert result[0].track_id == 17
