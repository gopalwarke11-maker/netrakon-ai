"""Focused tests for remote MP4 video URLs in NetraKon AI FILE camera sources.

Tests cover:
- Local FILE path detection
- HTTP URL detection
- HTTPS URL detection
- Invalid URL validation and error handling
- Cleanup of temporary downloaded file on release/stop
- Integration with CameraProcessor lifecycle
- Camera stream endpoint redirect behavior
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes.cameras import router as cameras_router
from app.main import app
from app.models.camera import CameraCreate
from app.services.camera_processor import (
    CameraProcessor,
    FileVideoSource,
    create_video_source,
    infer_source_type,
    is_remote_url,
    is_remote_video_url,
)
from app.services.camera_service import camera_service


def _create_minimal_mp4_bytes() -> bytes:
    """Generate a minimal valid 1-frame MP4 video in memory using OpenCV."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.putText(frame, "TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(tmp_path), fourcc, 10.0, (100, 100))
        for _ in range(5):
            writer.write(frame)
        writer.release()
        
        return tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_local_file_path_detection():
    assert not is_remote_url("clip.mp4")
    assert not is_remote_url(r"C:\videos\traffic.mp4")
    assert not is_remote_url("/var/data/camera.mp4")
    assert not is_remote_url(0)

    source = FileVideoSource("clip.mp4")
    assert not source.is_remote
    assert source.temp_path is None


def test_http_url_detection():
    url = "http://example.com/test_feed.mp4"
    assert is_remote_url(url)
    assert is_remote_video_url(url)

    source = FileVideoSource(url)
    assert source.is_remote
    assert infer_source_type(url) == "FILE"

    created_source = create_video_source(url)
    assert isinstance(created_source, FileVideoSource)
    assert created_source.is_remote


def test_https_url_detection():
    url = "https://cdn.example.org/videos/highway_cam01.mp4"
    assert is_remote_url(url)
    assert is_remote_video_url(url)

    source = FileVideoSource(url)
    assert source.is_remote
    assert infer_source_type(url) == "FILE"

    cam_model = CameraCreate(
        name="Highway Cam",
        sector="NORTH",
        location="Post 4",
        source_type="FILE",
        stream_url=url,
    )
    assert cam_model.source_type == "FILE"
    assert cam_model.stream_url == url


def test_invalid_url_handling():
    assert not is_remote_url("http://")
    assert not is_remote_url("https://")
    assert not is_remote_url("ftp://example.com/test.mp4")
    assert not is_remote_url("not_a_url")

    with pytest.raises(ValidationError, match="http or https"):
        CameraCreate(
            name="Bad Scheme",
            sector="NORTH",
            location="Post 1",
            source_type="FILE",
            stream_url="ftp://example.com/test.mp4",
        )

    with pytest.raises(ValidationError, match="include a host"):
        CameraCreate(
            name="No Host",
            sector="NORTH",
            location="Post 1",
            source_type="FILE",
            stream_url="http://",
        )

    source = FileVideoSource("http://invalid-unreachable-domain-99999.org/video.mp4")
    assert source.is_remote
    assert not source.open()
    assert source.temp_path is None


def test_cleanup_of_temporary_downloaded_file():
    mp4_bytes = _create_minimal_mp4_bytes()

    class MockResponse:
        status = 200
        def __init__(self, data: bytes):
            self.stream = io.BytesIO(data)
        def read(self, amt: int = -1):
            return self.stream.read(amt)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    url = "https://example.com/remote_sample.mp4"
    source = FileVideoSource(url)

    with patch("urllib.request.urlopen", return_value=MockResponse(mp4_bytes)):
        assert source.open()
        assert source.is_opened()
        assert source.temp_path is not None
        
        temp_file_path = source.temp_path
        assert temp_file_path.exists()
        assert temp_file_path.name.startswith("netrakon_")

        source.release()
        assert source.temp_path is None
        assert not temp_file_path.exists()


def test_remote_file_processor_lifecycle_and_cleanup():
    mp4_bytes = _create_minimal_mp4_bytes()

    class MockResponse:
        status = 200
        def __init__(self, data: bytes):
            self.stream = io.BytesIO(data)
        def read(self, amt: int = -1):
            return self.stream.read(amt)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    url = "https://example.com/remote_processor_test.mp4"
    processor = CameraProcessor(camera_id="CAM-REMOTE-01", source=url, source_type="FILE")

    with patch("urllib.request.urlopen", return_value=MockResponse(mp4_bytes)):
        status_res = processor.start()
        assert status_res.status in {"ONLINE", "PROCESSING"}

        source_obj = processor._source
        assert isinstance(source_obj, FileVideoSource)
        assert source_obj.temp_path is not None
        temp_file_path = source_obj.temp_path
        assert temp_file_path.exists()

        stopped_status = processor.stop()
        assert stopped_status.status == "STOPPED"
        assert not temp_file_path.exists()


def test_stream_endpoint_remote_url_redirect():
    client = TestClient(app)
    cam_payload = CameraCreate(
        name="Remote Stream Cam",
        sector="SECTOR-2",
        location="Gate 3",
        source_type="FILE",
        stream_url="https://example.com/remote_stream.mp4",
    )
    cam = camera_service.create(cam_payload)

    try:
        response = client.get(f"/api/cameras/{cam.id}/stream", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/remote_stream.mp4"
    finally:
        camera_service.delete(cam.id)
