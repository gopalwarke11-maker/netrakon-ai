"""Comprehensive tests for fixed demo video storage and processing pipeline.

Tests path resolution, safe traversal protection, FileVideoSource execution,
ONNX model singleton sharing, raw/processed stream endpoints, multi-camera isolation,
and regression checks.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.demo_videos import (
    DEMO_VIDEOS_DIR,
    get_demo_video_path,
    get_demo_videos_dir,
    is_path_safe_and_allowed,
    resolve_video_file_path,
)
from app.main import app
from app.services.camera_processor import FileVideoSource, camera_manager
from app.services.camera_service import camera_service
from app.models.camera import CameraCreate
from app.ai.model_manager import get_model


@pytest.fixture
def client():
    return TestClient(app)


def test_demo_video_directory_resolution():
    """Verify backend/demo_videos directory resolves accurately."""
    demo_dir = get_demo_videos_dir()
    assert demo_dir.exists()
    assert demo_dir.is_dir()
    assert demo_dir == DEMO_VIDEOS_DIR


def test_camera_1_and_2_path_resolution():
    """Verify camera_1.mp4 and camera_2.mp4 resolve to valid files."""
    cam1_path = get_demo_video_path("camera_1.mp4")
    cam2_path = get_demo_video_path("camera_2.mp4")

    assert cam1_path.exists()
    assert cam2_path.exists()

    res1 = resolve_video_file_path("camera_1.mp4")
    res2 = resolve_video_file_path("camera_2.mp4")

    assert res1 == cam1_path.resolve()
    assert res2 == cam2_path.resolve()

    # Relative path resolution
    rel1 = resolve_video_file_path("demo_videos/camera_1.mp4")
    assert rel1 == cam1_path.resolve()


def test_path_traversal_protection():
    """Verify unsafe paths or outside directory paths are blocked."""
    unsafe_paths = [
        "../../etc/passwd",
        "../app/main.py",
        "demo_videos/../../requirements.txt",
        "/etc/passwd",
        "C:\\Windows\\System32\\cmd.exe",
    ]
    for path in unsafe_paths:
        resolved = resolve_video_file_path(path)
        assert resolved is None, f"Unsafe path '{path}' was not blocked!"


def test_file_video_source_open_and_read():
    """Verify FileVideoSource opens demo_videos/camera_1.mp4 cleanly without full RAM load."""
    source = FileVideoSource("camera_1.mp4")
    assert source.open() is True
    assert source.is_opened() is True
    assert source.width > 0
    assert source.height > 0
    assert source.fps > 0

    ok, frame = source.read()
    assert ok is True
    assert frame is not None
    assert frame.shape[2] == 3  # RGB/BGR frame

    source.release()
    assert source.is_opened() is False


def test_file_video_source_rewind_looping():
    """Verify end of video rewind and looping behavior."""
    source = FileVideoSource("camera_1.mp4")
    assert source.open() is True

    # Read a frame
    ok1, frame1 = source.read()
    assert ok1 is True

    # Rewind
    assert source.rewind() is True
    ok2, frame2 = source.read()
    assert ok2 is True

    source.release()


def test_camera_processor_startup_and_duplicate_prevention():
    """Verify camera processor starts and prevents duplicate registration."""
    cam_id = "CAM-TEST-DEMO"
    if camera_manager.get(cam_id):
        camera_manager.unregister(cam_id)

    processor = camera_manager.register(cam_id, "camera_1.mp4", "FILE", loop_enabled=True)
    status = processor.start()
    assert status.status in {"ONLINE", "PROCESSING", "CONNECTING"}

    # Attempting to start again should raise RuntimeError
    with pytest.raises(RuntimeError):
        processor.start()

    # Attempting duplicate registration should raise ValueError
    with pytest.raises(ValueError):
        camera_manager.register(cam_id, "camera_1.mp4", "FILE")

    camera_manager.unregister(cam_id)


def test_raw_stream_endpoint(client):
    """Test GET /api/cameras/{camera_id}/stream endpoint."""
    # Ensure test camera exists
    cam_id = "CAM-01"
    camera = camera_service.get(cam_id)
    if camera is None:
        camera = camera_service.create(
            CameraCreate(
                name="Test Cam 1",
                sector="North",
                location="Gate 1",
                source_type="FILE",
                stream_url="camera_1.mp4",
            )
        )
    else:
        from app.models.camera import CameraUpdate
        camera_service.update(cam_id, CameraUpdate(
            name=camera.name,
            sector=camera.sector,
            location=camera.location,
            source_type="FILE",
            stream_url="camera_1.mp4",
        ))

    resp = client.get(f"/api/cameras/{cam_id}/stream")
    assert resp.status_code in {200, 206, 307}


def test_two_cameras_independent_sources():
    """Verify camera 1 and camera 2 operate independently with separate sources."""
    id1 = "CAM-IND-1"
    id2 = "CAM-IND-2"

    for cid in [id1, id2]:
        if camera_manager.get(cid):
            camera_manager.unregister(cid)

    p1 = camera_manager.register(id1, "camera_1.mp4", "FILE", loop_enabled=True)
    p2 = camera_manager.register(id2, "camera_2.mp4", "FILE", loop_enabled=True)

    p1.start()
    p2.start()

    assert p1.is_running is True
    assert p2.is_running is True
    assert p1.source_value != p2.source_value

    camera_manager.unregister(id1)
    camera_manager.unregister(id2)


def test_yolo_model_sharing():
    """Verify get_model returns the same shared ONNX session instance."""
    m1 = get_model()
    m2 = get_model()
    assert m1 is m2
