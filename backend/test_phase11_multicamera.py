"""Phase 11 camera lifecycle and state-isolation tests."""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from app.models.camera_processing import CameraProcessingStatus
from app.models.camera import CameraCreate
from app.services.camera_processor import (
    CameraDeviceSource,
    CameraManager,
    CameraProcessor,
    FileVideoSource,
    MJPEGVideoSource,
    RTSPVideoSource,
    create_video_source,
    infer_source_type,
)


class FakeSource:
    source_type = "FILE"
    width = 320
    height = 240
    fps = 10.0

    def __init__(self, source, source_type=None):
        self.source = source
        self.released = False
        self.release_event = threading.Event()

    def open(self):
        return True

    def read(self):
        if self.release_event.wait(0.001):
            return False, None
        return True, np.zeros((240, 320, 3), dtype=np.uint8)

    def is_opened(self):
        return not self.released

    def release(self):
        self.released = True
        self.release_event.set()


class FakeSession:
    def __init__(self, session_id, camera_id, model):
        self.session_id = session_id
        self.camera_id = camera_id
        self.model = model
        self.history = {1: object()}
        self.closed = False
        self.frames = []

    def process_frame(self, frame, frame_number, timestamp_ms=0.0):
        self.frames.append(frame_number)
        objects = [SimpleNamespace(track_id=1, confidence=0.9)]
        return SimpleNamespace(processing_time_ms=2.0, objects=objects)

    def close(self):
        self.closed = True


def make_processor(camera_id, sources=None, models=None):
    sources = sources if sources is not None else []
    models = models if models is not None else []

    def source_factory(source, source_type):
        item = FakeSource(source, source_type)
        sources.append(item)
        return item

    def session_factory(**kwargs):
        session = FakeSession(**kwargs)
        return session

    def model_factory():
        model = object()
        models.append(model)
        return model

    return CameraProcessor(
        camera_id,
        "sample.mp4",
        source_factory=source_factory,
        session_factory=session_factory,
        model_factory=model_factory,
    )


def test_camera_manager_creation():
    assert CameraManager().list_status() == []


def test_camera_registration():
    manager = CameraManager()
    processor = manager.register("CAM-01", "one.mp4", source_factory=lambda source, source_type: FakeSource(source, source_type), session_factory=FakeSession, model_factory=object)
    assert manager.get("CAM-01") is processor
    assert processor.status.status == "OFFLINE"


def test_duplicate_registration_is_rejected():
    manager = CameraManager()
    manager.register("CAM-01", "one.mp4")
    with pytest.raises(ValueError, match="already registered"):
        manager.register("CAM-01", "two.mp4")


def test_video_source_abstraction_types():
    assert isinstance(create_video_source("clip.mp4"), FileVideoSource)
    assert isinstance(create_video_source("rtsp://camera/stream"), RTSPVideoSource)
    assert isinstance(create_video_source("http://192.168.1.25:8080/video"), MJPEGVideoSource)
    assert isinstance(create_video_source("0"), CameraDeviceSource)
    assert infer_source_type(0) == "DEVICE"


def test_invalid_source_type_is_rejected_by_factory():
    with pytest.raises(ValueError):
        create_video_source("clip.mp4", "INVALID")  # type: ignore[arg-type]


def test_http_source_type_is_inferred_without_network_access():
    assert infer_source_type("https://camera.local/video") == "MJPEG"


def test_invalid_mjpeg_url_is_rejected():
    with pytest.raises(ValidationError, match="MJPEG cameras require"):
        CameraCreate(
            name="Phone",
            sector="SECTOR 1",
            location="Gate",
            source_type="MJPEG",
            stream_url="rtsp://camera/live",
        )


class ReconnectingFakeSource(FakeSource):
    source_type = "MJPEG"

    def __init__(self, source, source_type=None):
        super().__init__(source, source_type)
        self.open_count = 0

    def open(self):
        self.open_count += 1
        self.released = False
        return self.open_count >= 2

    def read(self):
        if self.open_count < 2:
            return False, None
        return True, np.zeros((240, 320, 3), dtype=np.uint8)


def test_network_source_reconnects_without_stopping_worker():
    source = ReconnectingFakeSource("http://camera/video", "MJPEG")
    processor = CameraProcessor(
        "CAM-IP",
        "http://camera/video",
        source_type="MJPEG",
        source_factory=lambda *_: source,
        session_factory=FakeSession,
        model_factory=object,
    )
    processor._network_retry_delay = 0.001
    processor.start()
    deadline = time.perf_counter() + 1.0
    while time.perf_counter() < deadline and processor.status.frames_processed < 2:
        time.sleep(0.01)
    status = processor.status
    processor.stop()
    assert status.frames_processed >= 2
    assert status.status in {"PROCESSING", "ONLINE"}
    assert source.open_count >= 2


def test_camera_start():
    processor = make_processor("CAM-01")
    status = processor.start()
    assert status.camera_id == "CAM-01"
    assert status.status in {"ONLINE", "PROCESSING", "STOPPED"}
    processor.stop()


def test_camera_stop_releases_source_and_session():
    sources = []
    processor = make_processor("CAM-01", sources=sources)
    processor.start()
    processor.stop()
    assert sources[0].released
    assert processor.status.status == "STOPPED"


def test_camera_restart_resets_transient_state():
    sources = []
    models = []
    processor = make_processor("CAM-01", sources=sources, models=models)
    processor.start()
    time.sleep(0.01)
    processor.stop()
    restarted = processor.restart()
    assert restarted.frames_processed == 0
    assert len(sources) == 2
    assert len(models) == 2
    processor.stop()


def test_camera_status_has_runtime_fields():
    processor = make_processor("CAM-01")
    status = processor.status
    assert isinstance(status, CameraProcessingStatus)
    assert status.frames_processed == 0
    assert status.detections_count == 0
    assert status.active_tracks == 0


def test_process_once_updates_metrics():
    processor = make_processor("CAM-01")
    processor._source = FakeSource("manual", "FILE")
    processor._session = FakeSession("CAM-01", "CAM-01", object())
    processor._status = CameraProcessingStatus(camera_id="CAM-01", status="ONLINE", source_type="FILE")
    processor._started_at = time.perf_counter()
    status = processor.process_once(np.zeros((240, 320, 3), dtype=np.uint8))
    assert status.frames_processed == 1
    assert status.detections_count == 1
    assert status.active_tracks == 1
    processor.stop()


def test_multiple_cameras_have_independent_processors():
    manager = CameraManager()
    first = manager.register("CAM-01", "one.mp4", source_factory=lambda source, source_type: FakeSource(source, source_type), session_factory=FakeSession, model_factory=object)
    second = manager.register("CAM-02", "two.mp4", source_factory=lambda source, source_type: FakeSource(source, source_type), session_factory=FakeSession, model_factory=object)
    assert first is not second
    assert {item.camera_id for item in manager.list_status()} == {"CAM-01", "CAM-02"}


def test_camera_sessions_receive_camera_identity():
    first = make_processor("CAM-01")
    second = make_processor("CAM-02")
    first.start()
    second.start()
    assert first.session.camera_id == "CAM-01"
    assert second.session.camera_id == "CAM-02"
    assert first.session is not second.session
    first.stop()
    second.stop()


def test_camera_sessions_receive_independent_models():
    models = []
    first = make_processor("CAM-01", models=models)
    second = make_processor("CAM-02", models=models)
    first.start()
    second.start()
    assert first.session.model is not second.session.model
    first.stop()
    second.stop()


def test_track_ids_are_scoped_by_camera_session():
    first = make_processor("CAM-01")
    second = make_processor("CAM-02")
    first.start()
    second.start()
    first.process_once(np.zeros((240, 320, 3), dtype=np.uint8))
    second.process_once(np.zeros((240, 320, 3), dtype=np.uint8))
    assert first.session.history is not second.session.history
    first.stop()
    second.stop()


def test_one_camera_failure_does_not_remove_other_camera():
    manager = CameraManager()
    healthy = manager.register("CAM-01", "one.mp4", source_factory=lambda source, source_type: FakeSource(source, source_type), session_factory=FakeSession, model_factory=object)
    failed = manager.register("CAM-02", "two.mp4", source_factory=lambda source, source_type: (_ for _ in ()).throw(RuntimeError("boom")), session_factory=FakeSession, model_factory=object)
    healthy.start()
    with pytest.raises(RuntimeError):
        failed.start()
    assert manager.get("CAM-01") is healthy
    assert healthy.status.status in {"ONLINE", "PROCESSING"}
    healthy.stop()


def test_duplicate_start_is_rejected():
    processor = make_processor("CAM-01")
    processor.start()
    with pytest.raises(RuntimeError, match="already running"):
        processor.start()
    processor.stop()


def test_stop_unregistered_camera_is_rejected():
    with pytest.raises(KeyError):
        CameraManager().stop("CAM-404")


def test_manager_status_is_camera_keyed():
    manager = CameraManager()
    manager.register("CAM-01", "one.mp4")
    manager.register("CAM-02", "two.mp4")
    statuses = manager.list_status()
    assert [status.camera_id for status in statuses] == ["CAM-01", "CAM-02"]


def test_manager_shutdown_cleans_all_workers():
    manager = CameraManager()
    manager.register("CAM-01", "one.mp4", source_factory=lambda source, source_type: FakeSource(source, source_type), session_factory=FakeSession, model_factory=object)
    manager.register("CAM-02", "two.mp4", source_factory=lambda source, source_type: FakeSource(source, source_type), session_factory=FakeSession, model_factory=object)
    manager.start("CAM-01")
    manager.start("CAM-02")
    manager.shutdown()
    assert all(status.status == "STOPPED" for status in manager.list_status())


def test_synthetic_video_source_can_be_opened(tmp_path):
    video_path = tmp_path / "camera.mp4"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (64, 48))
    assert writer.isOpened()
    writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    source = FileVideoSource(str(video_path))
    assert source.open()
    ok, frame = source.read()
    source.release()
    assert ok
    assert frame is not None


def test_two_synthetic_file_sources_run_simultaneously(tmp_path):
    paths = []
    for camera_number in (1, 2):
        video_path = tmp_path / f"camera_{camera_number}.mp4"
        writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
        assert writer.isOpened()
        for _ in range(5):
            writer.write(np.full((48, 64, 3), camera_number * 20, dtype=np.uint8))
        writer.release()
        paths.append(video_path)

    manager = CameraManager()
    for index, path in enumerate(paths, start=1):
        manager.register(
            f"CAM-0{index}",
            str(path),
            source_factory=lambda source, source_type: FileVideoSource(source),
            session_factory=FakeSession,
            model_factory=object,
        )

    manager.start("CAM-01")
    manager.start("CAM-02")
    deadline = time.perf_counter() + 2.0
    while time.perf_counter() < deadline:
        if all(manager.status(f"CAM-0{index}").frames_processed >= 5 for index in (1, 2)):
            break
        time.sleep(0.01)

    statuses = manager.list_status()
    manager.shutdown()
    assert {item.camera_id for item in statuses} == {"CAM-01", "CAM-02"}
    assert all(item.frames_processed == 5 for item in statuses)


def test_camera_source_read_failure_is_safe():
    source = FakeSource("missing", "FILE")
    assert source.open()
    source.release()
    ok, frame = source.read()
    assert not ok
    assert frame is None


class FiniteFakeSource(FakeSource):
    def __init__(self, source, source_type=None, frames_before_eof=2):
        super().__init__(source, source_type)
        self.frames_before_eof = frames_before_eof
        self.frames_read = 0
        self.open_count = 0

    def open(self):
        self.released = False
        self.open_count += 1
        self.frames_read = 0
        return True

    def read(self):
        if self.frames_read >= self.frames_before_eof:
            return False, None
        self.frames_read += 1
        return True, np.zeros((240, 320, 3), dtype=np.uint8)


def test_file_loop_reopens_at_eof_and_stays_live():
    sources = []

    def source_factory(source, source_type):
        item = FiniteFakeSource(source, source_type)
        sources.append(item)
        return item

    processor = CameraProcessor(
        "CAM-LOOP",
        "sample.mp4",
        loop_enabled=True,
        source_factory=source_factory,
        session_factory=FakeSession,
        model_factory=object,
    )
    processor.start()
    deadline = time.perf_counter() + 1.0
    while time.perf_counter() < deadline and processor.status.frames_processed < 5:
        time.sleep(0.01)
    status = processor.status
    processor.stop()
    assert status.frames_processed >= 5
    assert status.loop_enabled is True
    assert status.status in {"PROCESSING", "ONLINE"}
    assert sources[0].open_count >= 2


def test_file_without_loop_stops_at_eof():
    source = FiniteFakeSource("sample.mp4")
    processor = CameraProcessor(
        "CAM-FINITE",
        "sample.mp4",
        source_factory=lambda *_: source,
        session_factory=FakeSession,
        model_factory=object,
    )
    processor.start()
    deadline = time.perf_counter() + 1.0
    while time.perf_counter() < deadline and processor.status.status != "STOPPED":
        time.sleep(0.01)
    status = processor.status
    processor.stop()
    assert status.frames_processed == 2
    assert status.status == "STOPPED"
    assert status.loop_enabled is False


def test_restart_creates_new_track_session():
    processor = make_processor("CAM-01")
    processor.start()
    first_session = processor.session
    processor.stop()
    processor.restart()
    second_session = processor.session
    assert first_session is not second_session
    processor.stop()


def test_camera_event_ownership_contract_uses_camera_id():
    first = make_processor("CAM-01")
    second = make_processor("CAM-02")
    assert first.camera_id != second.camera_id
    assert first.status.camera_id == "CAM-01"
    assert second.status.camera_id == "CAM-02"
